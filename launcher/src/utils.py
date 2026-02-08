import os
import json
import time
import base64
import hashlib
import requests

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from game_state import GameState

# Global Thread Pool for both long-running servers and short-lived tasks
executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 2)
LOGIN_DATA = "TddjSAPGzlIBXo5/eXRfw+slaoO/7ofwM5vWQnQ0zkLRelV7qVdCDH/Sn5qVjtdfo/Xm+6vXBvzZtqmUFkvRiPdr2l5aQ8cJx8980VZ5/pbr0cXy3Dy8jYVtcNrnQ8N0izNJAe8k3RJzuleig9CXwIF+MGTWuyUrqGavjD3M8WVMru8SeNAjIUjVXx3kqdVXETfBJKW0lIM5mszDTp46Vozewbn+wRfCDCJ6dC4h8E7aQ/M1HchDDvWS8kUS64cIRqrSGW6UBbnFxjAzWbwtyQP3w/tqWmfhNgkjDFMTmooZxhkmsP42PWO4crpJ+mkzKzH29Xo69gH6aAjhfaFN15Nv6AZQfxUPDmBEqKIbJ2RsX3fSSdqzNvfzjGeg6x9LWzq/6It9RPQXgCDw8Iavvj9m+Bmo+fd5VkcXR1eS52xIPqqscx4Vg/hy1KGardvxtXL9907jfAG0AEHDbaVKmeYvRdIzI1ukaLM4krCy11ugPypEx4GTLlqp9vWkog1GNQUNNDOh3F+/PBw0M+wvbQ=="
API_LATEST_BUILD = "https://loadingbaycn.webapp.163.com/app/v1/file_distribution/latest_build?app_ids=[{game_id}]"
API_MANIFEST_URL = "https://loadingbaycn.webapp.163.com/app/v1/file_distribution_v2/manifest_url?app_content_id={content_id}&target_version={version_code}"

def request_get(url: str, params: dict = None) -> dict:
    for i in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[!] Request failed: {e}")
            time.sleep(i * 2)

def parse_game_state(dir_path: Path, game_id: int):
    if isinstance(dir_path, str):
        dir_path = Path(dir_path)
    state_path = dir_path / ".dlstorage" / "downloading" / f"{game_id}_app.state"
    if not state_path.exists():
        return None
        
    try:
        with open(state_path, 'r') as f:
            state_data = json.load(f)
            return GameState.from_dict(state_data)
    except Exception:
        return None

def encode_path(path: str) -> str:
    if not path:
        return ""
    return base64.b64encode(path.encode('utf-8')).decode('utf-8')

def get_latest_version(game_id: int) -> dict:
    api = API_LATEST_BUILD.format(game_id=game_id)
    try:
        data = request_get(api)
        if data is not None and data.get("code") == 200:
            apps: dict = data.get("data", {}).get("apps", [])
            if apps:
                app = apps[0]
                return {
                    "version": app.get("version_code", ""),
                    "app_id": app.get("app_id", 0),
                    "content_id": app.get("main_content_id", 0),
                    "running_process_name": app.get("running_process_name", "")
                }
    except Exception:
        pass
    return None

def get_downloadable_id(content_id: int, version_code: str) -> int:
    if version_code is None or version_code.strip() == "":
        return 0
    default_id = int(version_code.split("_")[1]) if version_code and "_" in version_code else 0
    api = API_MANIFEST_URL.format(content_id=content_id, version_code=version_code)
    try:
        data = request_get(api)
        if data is not None and data.get("code") == 200:
            downloadable_id = data.get("data", {}).get("downloadable_id", default_id)
            return downloadable_id if downloadable_id is not None else default_id
    except Exception:
        pass
    return default_id

def check_resource(base_path: str, game_id: int, content_id: int, progress_callback=None) -> list[str]:
    repair_file_list = []
    state_path = Path(base_path) / ".dlstorage" / "downloading" / f"{game_id}_app.state"
    if not state_path.exists():
        return repair_file_list
    
    game_state = parse_game_state(base_path, game_id)
    if game_state is None or game_state.StateFlag != 8:
        return repair_file_list
    
    def verify_file(file_info: dict) -> str | None:
        if file_info.get("dir", 0) != 0: return None
        name = file_info.get("name", "")
        md5 = file_info.get("md5", "")
        if not name or not md5: return None
        
        target = Path(base_path) / Path(name)
        if not target.exists(): return name
        try:
            with open(target, 'rb') as f:
                file_md5 = hashlib.md5(f.read()).hexdigest()
            if file_md5 != md5: return name
        except Exception: return name
        return None

    try:
        content_info = game_state.installed_contents.get(str(content_id))
        downloadable_id = content_info.DownloadableId if content_info else None
        manifest_path = Path(base_path) / ".dlstorage" / "depotcache" / f"{content_id}_{downloadable_id}.manifest"
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest_data: dict = json.load(f)
                
            file_list = manifest_data.get("files", [])
            total = len(file_list)
            
            from concurrent.futures import as_completed
            futures = [executor.submit(verify_file, f) for f in file_list]
            
            for i, future in enumerate(as_completed(futures)):
                res = future.result()
                if res:
                    repair_file_list.append(res)
                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(i + 1, total)
    except Exception as e:
        print(f"Error reading state file: {e}")

    return repair_file_list

def patch_login(base_path: str):
    target_path = Path(base_path) / "netease.data"
    with open(target_path, 'wb') as f:
        f.write(base64.b64decode(LOGIN_DATA))