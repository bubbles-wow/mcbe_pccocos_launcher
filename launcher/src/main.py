import tkinter as tk
import ctypes
import os
import sys
import logging

from pathlib import Path
from datetime import datetime

from config import ConfigWrapper
from core import DownloaderCore
from gui import DownloaderGUI

BASE_PATH = Path(__file__).parent

def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s.%(msecs)03d][%(levelname)s] (%(name)s): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def set_dpi_awareness():
    try:
        # Windows 10+
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # Windows 8.1
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def main():
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    setup_logging()
    set_dpi_awareness()
    
    config_path = BASE_PATH / "config.json"
    config_wrapper = ConfigWrapper.load(config_path)
    
    core = DownloaderCore(BASE_PATH, config_wrapper)
    
    root = tk.Tk()
    app = DownloaderGUI(root, core)
    
    core.log_callback = app.log
    
    root.mainloop()

if __name__ == "__main__":
    main()
