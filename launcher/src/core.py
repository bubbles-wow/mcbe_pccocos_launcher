import os
import json
import subprocess
import threading
import zmq
import tempfile
import logging

from pathlib import Path
from config import ConfigWrapper
from utils import (
    executor, get_latest_version, parse_game_state, 
    patch_login, get_downloadable_id
)
from progress import DownloadProgress

class DownloaderCore:
    def __init__(self, base_path: Path, config: ConfigWrapper = None, log_callback: callable = None, progress_callback: callable = None):
        self.base_path = base_path
        self.config_wrapper = config if config else ConfigWrapper.load()
        self.download_config = self.config_wrapper.downloadConfig
        self.app_config = self.config_wrapper.appConfig
        self.game_config = self.config_wrapper.gameConfig
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.stop_event = threading.Event()
        self.manifest_thread = None
        self.server_thread = None
        self.download_thread = None
        self.process = None
        self.game_process = None
        self.last_cid = None
        self.ipc_stop_requested = threading.Event()
        self.manifest_server = None

    def is_game_running(self):
        if self.game_process and self.game_process.poll() is None:
            return True
        return False

    def log(self, message):
        logging.info(message)
        if self.log_callback:
            self.log_callback(message)

    def fetch_latest_version(self):
        try:
            result = get_latest_version(self.game_config.app_id)
            if result:
                self.download_config.targetVersion = result["version"]
                self.game_config.app_id = result["app_id"]
                self.game_config.content_id = result["content_id"]
                self.game_config.running_process = result["running_process_name"]
                self.config_wrapper.save()
                return result
        except Exception as e:
            self.log(f"Fetch version error: {e}")
        return None

    def detect_local_state(self):
        state = parse_game_state(self.game_config.path, self.game_config.app_id)
        if not state:
            return None
            
        if state.AppId != str(self.game_config.app_id):
            self.game_config.app_id = int(state.AppId)
            
        origin_v = state.get_version(self.game_config.content_id, staged=False)
        if origin_v:
            self.download_config.originVersion = origin_v
        else:
            self.download_config.originVersion = ""
            
        target_v = state.get_version(self.game_config.content_id, staged=True)
        if target_v:
            self.download_config.targetVersion = target_v
        else:
            self.download_config.targetVersion = ""
            
        self.config_wrapper.save()
        
        flag = state.StateFlag
        analysis = {
            "state_flag": flag,
            "origin_v": self.download_config.originVersion,
            "target_v": self.download_config.targetVersion,
            "is_interrupted": 2 < flag < 8,
            "is_repair_mode": False,
            "repair_files": []
        }
        
        if analysis["is_interrupted"]:
            staged_content = state.staged_contents.get(str(self.game_config.content_id))
            if staged_content and staged_content.Mode == 3:
                analysis["is_repair_mode"] = True
                analysis["repair_files"] = staged_content.RepairFiles
                
        return analysis

    def check_for_updates(self):
        latest = self.fetch_latest_version()
        if not latest:
            return {"success": False, "has_update": False}
            
        try:
            origin_id = get_downloadable_id(self.game_config.content_id, self.download_config.originVersion)
            target_id = get_downloadable_id(self.game_config.content_id, self.download_config.targetVersion)
            
            has_update = origin_id < target_id
            return {
                "success": True, 
                "has_update": has_update, 
                "latest_version": latest["version"]
            }
        except Exception as e:
            self.log(f"Update comparison error: {e}")
            return {"success": False, "has_update": False, "error": str(e)}

    def verify_integrity(self, progress_callback=None):
        from utils import check_resource
        return check_resource(
            self.game_config.path, 
            self.game_config.app_id, 
            self.game_config.content_id,
            progress_callback=progress_callback
        )

    def stop(self):
        self.log("Stopping all tasks...")
        
        if self.process:
            try:
                if self.last_cid:
                    self.log("Requesting IPC stop via ZMQ...")
                    self.ipc_stop_requested.set()
                    try:
                        self.process.wait(timeout=3)
                        self.log("Subprocess exited via ZMQ request.")
                    except subprocess.TimeoutExpired:
                        self.log("Subprocess did not exit gracefully, killing...")
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], capture_output=True)
                        else:
                            self.process.terminate()
                else:
                    self.log("No ZMQ CID available, terminating process directly.")
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], capture_output=True)
                    else:
                        self.process.terminate()
            except Exception as e:
                self.log(f"Error terminating process: {e}")
            finally:
                self.process = None
        
        self.cleanup_servers()
        self.log("Cleanup request sent.")

    def cleanup_servers(self):
        self.stop_event.set()
        
        if self.manifest_server:
            try:
                self.manifest_server.shutdown()
                self.manifest_server = None
                self.log("Manifest server stopped.")
            except Exception as e:
                self.log(f"Error shutting down manifest server: {e}")
        
    def start_servers(self):
        self.start_manifest_server()
        self.start_zmq_server()

    def start_manifest_server(self):
        if self.manifest_thread and self.manifest_thread.is_alive():
            return
            
        self.log("Starting manifest server...")
        try:
            from manifest_server import app as manifest_app
            from werkzeug.serving import make_server
            
            self.manifest_server = make_server('127.0.0.1', 7000, manifest_app)
            def run_flask():
                if self.manifest_server:
                    self.manifest_server.serve_forever()
                    
            self.manifest_thread = threading.Thread(target=run_flask, daemon=True)
            self.manifest_thread.start()
        except Exception as e:
            self.log(f"Failed to start manifest server: {e}")

    def start_zmq_server(self):
        if self.server_thread and self.server_thread.is_alive():
            return
        self.log("Starting ZMQ server...")
        self.server_thread = threading.Thread(target=self.run_zmq_server, daemon=True)
        self.server_thread.start()

    def run_zmq_server(self):
        sub_port = self.download_config.pubport
        pub_port = self.download_config.subport
        
        ctx = zmq.Context()
        sub_sock = ctx.socket(zmq.SUB)
        sub_sock.bind(f"tcp://127.0.0.1:{sub_port}")
        sub_sock.setsockopt_string(zmq.SUBSCRIBE, "")
        
        pub_sock = ctx.socket(zmq.PUB)
        pub_sock.bind(f"tcp://127.0.0.1:{pub_port}")
        
        poller = zmq.Poller()
        poller.register(sub_sock, zmq.POLLIN)

        try:
            while not self.stop_event.is_set():
                if self.ipc_stop_requested.is_set():
                    self.ipc_stop_requested.clear()
                    if self.last_cid:
                        pub_sock.send_multipart([self.last_cid, b"3"])
                        pub_sock.send_multipart([self.last_cid, b"3"])
                        self.log("Sent stop signal to IPC via ZMQ.")
                        return

                socks = dict(poller.poll(timeout=100))
                if sub_sock in socks:
                    parts = sub_sock.recv_multipart()
                    if len(parts) != 3: continue
                    
                    self.last_cid = parts[0]
                    cid = self.last_cid
                    try:
                        m_type_str = parts[1].decode('utf-8', errors='replace')
                        m_type = int(m_type_str) if m_type_str.isdigit() else 0
                        data_raw = parts[2].decode('utf-8', errors='replace')
                    except Exception: continue
                    
                    if m_type == 10 and parts[2] == b"heartbeat":
                        pub_sock.send_multipart([cid, b"4"])
                        continue
                    elif 3 <= m_type <= 8:
                        data = json.loads(data_raw)
                        if self.progress_callback:
                            progress_obj = DownloadProgress.from_dict(data)
                            self.progress_callback(progress_obj)
                            
                    if 8 <= m_type < 2000:
                        pub_sock.send_multipart([cid, b"3"])
                        pub_sock.send_multipart([cid, b"3"])
                        self.log(f"Received stop signal from IPC (type {m_type})")
                        return
        except Exception as e:
            self.log(f"ZMQ Server Error: {e}")
        finally:
            sub_sock.close()
            pub_sock.close()
            ctx.term()
            self.log("ZMQ server stopped.")

    def start_download(self, on_finished_callback=None):
        self.stop_event.clear()
        self.start_servers()
        
        def runner():
            try:
                self.execute_binary()
            finally:
                self.cleanup_servers()
                if on_finished_callback:
                    on_finished_callback()

        self.download_thread = executor.submit(runner)

    def execute_binary(self):
        exe_path = self.base_path / "bin" / "downloadIPC.exe"
        self.last_cid = None # Reset CID for new execution
        
        if not exe_path.exists():
            self.log(f"Error: Could not find {exe_path}")
            return

        param = self.download_config.to_dict()
        param["gameid"] = self.game_config.app_id
        param["contentid"] = self.game_config.content_id
        param["path"] = self.game_config.path
        
        # Ensure paths are base64 encoded
        from utils import encode_path
        param["path"] = encode_path(param.get("path", ""))
        param["repairListPath"] = encode_path(param.get("repairListPath", ""))
        
        cmd = [str(exe_path)]
        for k, v in param.items():
            cmd.append(f"--{k}:{v}")
            
        self.log(f"Starting downloader... ({' '.join(cmd)})")
        
        self.process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            encoding='utf-8', 
            errors='replace', 
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        stdout, stderr = self.process.communicate()
        if self.process.returncode != 0:
            self.log(f"Process downloadIPC.exe error (code {self.process.returncode}): {stderr}")
        else:
            self.log("Process downloadIPC.exe stopped.")
        self.process = None
        
    def launch_game(self):
        if self.is_game_running():
            self.log("Game instance already detected. Cannot launch multiple instances.")
            return None

        if not self.game_config.running_process or not self.game_config.path:
            self.log("No running process or path configured to launch.")
            return None
        
        try:
            patch_login(self.game_config.path)
            # We use shell=True and cwd to ensure the executable is found in the game directory
            # and that it can load its dependencies.
            self.game_process = subprocess.Popen(
                f'"{self.game_config.running_process}" --start_from_launcher=1', 
                shell=True, 
                cwd=self.game_config.path
            )
            self.log(f"Launching game: {self.game_config.running_process} (CWD: {self.game_config.path})")
        except Exception as e:
            self.log(f"Failed to launch game: {e}")
            return None
            
    def repair_files(self, repair_list: list[str], on_finished_callback=None):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.txt') as tmp:
            tmp.write("\n".join(repair_list))
            tmp_path = tmp.name
            
        self.download_config.targetVersion = self.download_config.originVersion
        self.download_config.isRepairMode = 1
        self.download_config.repairListPath = tmp_path

        def cleanup():
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            self.download_config.isRepairMode = 0
            self.download_config.repairListPath = ""
            if on_finished_callback:
                on_finished_callback()

        self.start_download(on_finished_callback=cleanup)
