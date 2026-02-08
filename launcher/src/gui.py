import tkinter as tk
import os

from tkinter import ttk, filedialog, messagebox
from i18n import I18N
from progress import DownloadProgress
from utils import executor
from core import DownloaderCore

class DownloaderGUI:
    def __init__(self, root: tk.Tk, core: DownloaderCore):
        self.core = core
        # Setup callbacks
        self.core.log_callback = self.log
        self.core.progress_callback = self.on_progress

        self.config_wrapper = core.config_wrapper
        self.download_config = core.download_config
        self.app_config = core.app_config
        self.game_config = core.game_config
        
        self.root = root
        self.lang = 'zh'
        self.texts = I18N[self.lang]

        # Initialize core variables before UI setup
        self.path_var = tk.StringVar(value=self.game_config.path)
        self.version_var = tk.StringVar(value=self.download_config.targetVersion)
        
        if self.app_config.silentMode:
            self.root.withdraw()
        else:
            self.root.title(self.texts['title'])
            self.root.geometry("1024x768")
            self.create_widgets()
            
        # 0: ready, 1: downloading, 2: checking
        self.app_state = 0
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Async fetch version
        self.root.after(0, self.check_path)
        
        self.root.after(2000, self.monitor_game_status)

    def set_controls_state(self, enabled: bool):
        state = 'normal' if enabled else 'disabled'
        widgets = [
            'start_button', 'launch_button', 'repair_button',
            'browse_btn', 'check_version_btn', 'path_entry', 'version_entry'
        ]
        for w_name in widgets:
            widget = getattr(self, w_name, None)
            if widget:
                try:
                    widget.config(state=state)
                except Exception:
                    pass
        
        if enabled and hasattr(self, 'repair_button'):
            try:
                self.repair_button.config(text=self.texts['check_integrity_btn'])
            except Exception:
                pass

    def fetch_latest_version(self):
        self.log(self.texts['checking_version'])
        self.set_controls_state(False)
            
        def task():
            try:
                result = self.core.check_for_updates()
                if result.get("success"):
                    version = result["latest_version"]
                    self.root.after(0, lambda: self.version_var.set(version))
                    self.root.after(0, lambda: self.log(self.texts['fetch_success'].format(version=version)))
                    
                    if result["has_update"]:
                        if self.app_config.autoUpdate:
                            self.root.after(0, self.start_download)
                        else:
                            def ask_update():
                                if messagebox.askyesno(self.texts['update_confirm_title'], self.texts['update_confirm_msg']):
                                    self.start_download()
                                elif self.app_config.silentMode:
                                    self.exit_and_launch()
                            self.root.after(0, ask_update)
                    elif self.app_config.silentMode:
                        self.root.after(0, self.exit_and_launch)
                else:
                    self.root.after(0, lambda: self.log(self.texts['fetch_failed']))
                    if self.app_config.silentMode:
                        self.root.after(0, self.exit_and_launch)
            finally:
                is_running = (self.core.download_thread and not self.core.download_thread.done())
                if not is_running:
                    self.root.after(0, lambda: self.set_controls_state(True))
        
        executor.submit(task)
        
    def check_path(self):
        analysis = self.core.detect_local_state()
        if analysis:
            if analysis['origin_v']:
                self.log(self.texts['detected_origin_v'].format(version=analysis['origin_v']))
            if analysis['target_v']:
                self.version_var.set(analysis['target_v'])
                self.log(self.texts['detected_target_v'].format(version=analysis['target_v']))
            
            if analysis['is_interrupted']:
                if self.app_config.autoUpdate:
                    self.log(self.texts['continuing_download'].format(flag=analysis['state_flag']))
                    if analysis['is_repair_mode']:
                        self.download_config.originVersion = analysis['target_v']
                        self.version_var.set(analysis['target_v'])
                        self.set_controls_state(False)
                        self.core.repair_files(
                            analysis['repair_files'], 
                            on_finished_callback=lambda: self.root.after(0, self.on_finished)
                        )
                    else:
                        self.start_download()
                    return
                else:
                    def ask_continue():
                        if messagebox.askyesno(self.texts['continue_download_title'], 
                                             self.texts['continue_download_msg'].format(flag=analysis['state_flag'])):
                            self.log(self.texts['continuing_download'].format(flag=analysis['state_flag']))
                            if analysis['is_repair_mode']:
                                self.download_config.originVersion = analysis['target_v']
                                self.version_var.set(analysis['target_v'])
                                self.set_controls_state(False)
                                self.core.repair_files(
                                    analysis['repair_files'], 
                                    on_finished_callback=lambda: self.root.after(0, self.on_finished)
                                )
                            else:
                                self.start_download()
                        elif self.app_config.silentMode:
                            self.exit_and_launch()
                        else:
                            self.fetch_latest_version()

                    self.root.after(0, ask_continue)
                    return
                    
        self.fetch_latest_version()

    def create_widgets(self):
        # Master grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        style = ttk.Style()
        style.configure('Main.TLabelframe', padding=10)
        padding = {'padx': 15, 'pady': 8}

        # --- Input Section ---
        self.input_frame = ttk.LabelFrame(self.root, text=self.texts['config_section'], style='Main.TLabelframe')
        self.input_frame.grid(row=0, column=0, sticky='ew', **padding)
        self.input_frame.columnconfigure(1, weight=1)

        ttk.Label(self.input_frame, text=self.texts['path_label']).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.path_var.trace_add("write", self._on_path_changed)
        self.path_entry = ttk.Entry(self.input_frame, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=1, sticky='ew', padx=5)
        self.browse_btn = ttk.Button(self.input_frame, text=self.texts['browse_btn'], width=10, command=self.browse_path)
        self.browse_btn.grid(row=0, column=2, padx=5)

        ttk.Label(self.input_frame, text=self.texts['version_label']).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.version_var.trace_add("write", self._on_version_changed)
        self.version_entry = ttk.Entry(self.input_frame, textvariable=self.version_var)
        self.version_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        self.check_version_btn = ttk.Button(self.input_frame, text=self.texts['check_version_btn'], width=10, command=self.fetch_latest_version)
        self.check_version_btn.grid(row=1, column=2, padx=5)

        # --- Progress Section ---
        self.progress_frame = ttk.LabelFrame(self.root, text=self.texts['status_section'], style='Main.TLabelframe')
        # Initially hidden
        self.progress_frame.columnconfigure(0, weight=1)

        def create_progress_block(parent, title):
            container = ttk.Frame(parent)
            # pack will be handled dynamically
            
            header_frame = ttk.Frame(container)
            header_frame.pack(fill='x')
            ttk.Label(header_frame, text=title, font=('Microsoft YaHei', 9, 'bold')).pack(side='left')
            status_lbl = ttk.Label(header_frame, text=self.texts['ready_status'], foreground='#666')
            status_lbl.pack(side='right')
            
            bar = ttk.Progressbar(container, orient='horizontal', mode='determinate')
            bar.pack(fill='x', pady=(2, 0))
            return container, bar, status_lbl

        self.index_container, self.index_progress, self.index_status = create_progress_block(self.progress_frame, self.texts['indexing_title'])
        self.download_container, self.download_progress, self.download_status = create_progress_block(self.progress_frame, self.texts['downloading_title'])
        self.build_container, self.build_progress, self.build_status = create_progress_block(self.progress_frame, self.texts['building_title'])
        self.integrity_container, self.integrity_progress, self.integrity_status = create_progress_block(self.progress_frame, self.texts['integrity_title'])

        # --- Control Section ---
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.grid(row=1, column=0, sticky='ew', padx=15, pady=10)
        self.control_frame.columnconfigure(0, weight=2)
        self.control_frame.columnconfigure(1, weight=2)
        self.control_frame.columnconfigure(2, weight=1)

        self.start_button = tk.Button(
            self.control_frame, 
            text=self.texts['start_btn'], 
            command=self.start_download,
            bg='#28a745', 
            fg='white', 
            font=('Microsoft YaHei', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            activebackground='#218838',
            activeforeground='white',
            pady=5
        )
        self.start_button.grid(row=0, column=0, sticky='ew', padx=(0, 2))

        self.launch_button = tk.Button(
            self.control_frame, 
            text=self.texts['launch_btn'], 
            command=self.core.launch_game,
            bg='#0078d4', 
            fg='white', 
            font=('Microsoft YaHei', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            activebackground='#005a9e',
            activeforeground='white',
            pady=5
        )
        self.launch_button.grid(row=0, column=1, sticky='ew', padx=2)

        self.repair_button = tk.Button(
            self.control_frame, 
            text=self.texts['check_integrity_btn'], 
            command=self.check_file_integrity,
            bg="#0063ba", 
            fg='white', 
            font=('Microsoft YaHei', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            activebackground='#5a6268',
            activeforeground='white',
            pady=5
        )
        self.repair_button.grid(row=0, column=2, sticky='ew', padx=(2, 0))

        # --- Log Section ---
        self.log_frame = ttk.LabelFrame(self.root, text=self.texts['log_section'], style='Main.TLabelframe')
        self.log_frame.grid(row=3, column=0, sticky='nsew', **padding)
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            self.log_frame, 
            font=('Consolas', 9), 
            bg='#ffffff', 
            relief='flat',
            highlightthickness=1,
            highlightbackground='#dee2e6'
        )
        self.log_text.grid(row=0, column=0, sticky='nsew')
        
        sb = ttk.Scrollbar(self.log_frame, orient='vertical', command=self.log_text.yview)
        sb.grid(row=0, column=1, sticky='ns')
        self.log_text.config(yscrollcommand=sb.set)

    def _on_path_changed(self, *args):
        self.game_config.path = self.path_var.get()
        self.config_wrapper.save()

    def _on_version_changed(self, *args):
        self.download_config.targetVersion = self.version_var.get()
        if self.download_config.originVersion == self.download_config.targetVersion and hasattr(self, 'start_button'):
            self.start_button.config(state='disabled')
        else:
            self.start_button.config(state='normal')

    def browse_path(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.path_var.set(dir_path)
            self.check_path()

    def on_closing(self):
        if self.app_state == 0 or messagebox.askokcancel(
            self.texts['exit_title'], 
            self.texts['exit_msg']):
                self.core.stop()
                self.root.destroy()
                os._exit(0)

    def show_compact_ui(self):
        if not self.app_config.silentMode:
            return
            
        if not hasattr(self, 'index_container'):
            self.create_widgets()
            
        if hasattr(self, 'input_frame'): self.input_frame.grid_forget()
        if hasattr(self, 'control_frame'): self.control_frame.grid_forget()
        if hasattr(self, 'log_frame'): self.log_frame.grid_forget()
        
        self.progress_frame.grid(row=0, column=0, sticky='nsew', padx=15, pady=20)
        self.root.title(f"{self.texts['title']} - Progress")
        self.root.geometry("1024x220")
        self.root.deiconify()

    def exit_and_launch(self):
        self.core.launch_game()
        self.root.destroy()
        os._exit(0)

    def monitor_game_status(self):
        if self.app_config.silentMode and not hasattr(self, 'launch_button'):
            self.root.after(2000, self.monitor_game_status)
            return

        try:
            is_running = self.core.is_game_running()
            
            if is_running:
                if self.launch_button['text'] != self.texts['game_running']:
                    self.launch_button.config(text=self.texts['game_running'])
                    self.set_controls_state(False)
            else:
                if self.launch_button['text'] == self.texts['game_running']:
                    self.launch_button.config(text=self.texts['launch_btn'])
                    
                    is_task_running = (self.core.download_thread and not self.core.download_thread.done()) or \
                                     (self.repair_button['text'] == self.texts['initializing'])
                                     
                    if not is_task_running:
                        self.set_controls_state(True)
        finally:
            self.root.after(2000, self.monitor_game_status)

    def log(self, message):
        if not self.app_config.silentMode:
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)

    def on_progress(self, data: DownloadProgress):
        status = data.StateFlags
        if status == 3:
            p = data.ShowDownloadHeadPercent
            r = data.ShowDownloadHeadRateStr
            s = data.ShowDownloadHeadSize
            sz_str = f"{s / (1024*1024):.2f} MB"
            
            # Switch visibility: Indexing only
            self.root.after(0, lambda: self.index_container.pack(fill='x', pady=5))
            self.root.after(0, self.download_container.pack_forget)
            self.root.after(0, self.build_container.pack_forget)
            
            self.root.after(0, lambda: self.update_index_ui(p, r, sz_str))
        elif 4 <= status <= 8:
            dp = data.ShowDownloadPercent
            dr = data.ShowDownloadRateStr
            ds = data.ShowDownloadSize
            ds_str = f"{ds / (1024*1024):.2f} MB"
            
            bp = data.ShowBuildPercent
            br = data.ShowBuildRateStr
            bs = data.ShowBuildSize
            bs_str = f"{bs / (1024*1024):.2f} MB"

            # Switch visibility: Download & Build
            self.root.after(0, self.index_container.pack_forget)
            self.root.after(0, lambda: self.download_container.pack(fill='x', pady=5))
            self.root.after(0, lambda: self.build_container.pack(fill='x', pady=5))
            
            self.root.after(0, lambda: self.update_main_ui(dp, dr, ds_str, bp, br, bs_str))

    def update_index_ui(self, p, r, s):
        self.index_progress['value'] = p * 100
        self.index_status.config(text=self.texts['progress_format'].format(percent=p*100, rate=r, status=s))

    def update_main_ui(self, dp, dr, ds, bp, br, bs):
        self.download_progress['value'] = dp * 100
        self.download_status.config(text=self.texts['progress_format'].format(percent=dp*100, rate=dr, status=ds))
        self.build_progress['value'] = bp * 100
        self.build_status.config(text=self.texts['progress_format'].format(percent=bp*100, rate=br, status=bs))

    def start_download(self):
        self.app_state = 1
        if self.core.download_thread and not self.core.download_thread.done():
            messagebox.showwarning(self.texts['exit_title'], self.texts['downloading_warning'])
            return

        if not self.game_config.path or not self.download_config.targetVersion:
            messagebox.showerror(self.texts['exit_title'], self.texts['path_version_error'])
            return

        if self.app_config.silentMode:
            self.show_compact_ui()

        self.set_controls_state(False)
        # Show progress frame when starting
        self.progress_frame.grid(row=2, column=0, sticky='ew', padx=15, pady=5)
        self.core.start_download(on_finished_callback=lambda: self.root.after(0, self.on_finished))

    def check_file_integrity(self):
        self.app_state = 2
        if not self.game_config.path:
            messagebox.showerror(self.texts['exit_title'], self.texts['path_error'])
            return

        if self.app_config.silentMode:
            self.show_compact_ui()

        self.version_var.set(self.download_config.originVersion)
        self.set_controls_state(False)
        self.repair_button.config(text=self.texts['initializing'])
        
        # Show progress UI
        self.progress_frame.grid(row=2, column=0, sticky='ew', padx=15, pady=5)
        self.integrity_container.pack(fill='x', pady=5)
        self.integrity_progress['value'] = 0
        self.integrity_status.config(text=self.texts['initializing'])
        
        self.log(self.texts['starting_integrity_check'])

        def task():
            try:
                def on_check_progress(curr, total):
                    p = (curr / total) * 100
                    self.root.after(0, lambda: self.integrity_progress.config(value=p))
                    self.root.after(0, lambda: self.integrity_status.config(text=self.texts['check_progress'].format(curr=curr, total=total, percent=p)))

                repair_file_list = self.core.verify_integrity(progress_callback=on_check_progress)
                self.root.after(0, lambda: self._on_integrity_checked(repair_file_list))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(self.texts['exit_title'], self.texts['check_failed'].format(error=str(e))))
                self.root.after(0, self.on_finished)

        executor.submit(task)

    def _on_integrity_checked(self, repair_file_list):
        self.log(self.texts['task_finished'])
        if len(repair_file_list) == 0:
            messagebox.showinfo(self.texts['check_complete_title'], self.texts['check_intact_msg'])
            self.on_finished()
            return
            
        if not messagebox.askyesno(self.texts['repair_title'], self.texts['repair_msg'].format(count=len(repair_file_list))):
            if self.app_config.silentMode:
                self.exit_and_launch()
            else:
                self.on_finished()
            return
            
        self.log(self.texts['repairing_files'].format(count=len(repair_file_list)))
        if self.app_config.silentMode:
            self.show_compact_ui()

        self.set_controls_state(False)
        
        self.progress_frame.grid(row=2, column=0, sticky='ew', padx=15, pady=5)
        self.core.repair_files(
            repair_file_list, 
            on_finished_callback=lambda: self.root.after(0, self.on_finished)
        )

    def on_finished(self):
        self.app_state = 0
        if self.app_config.silentMode:
            self.exit_and_launch()
            return
            
        self.set_controls_state(True)
        # Hide progress elements
        self.index_container.pack_forget()
        self.download_container.pack_forget()
        self.build_container.pack_forget()
        self.integrity_container.pack_forget()
        self.progress_frame.grid_forget()
        # Recheck local state to update UI
        self.check_path()
        self.log(self.texts['task_finished'])
