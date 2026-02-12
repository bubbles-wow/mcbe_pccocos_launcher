import json
import logging

from dataclasses import dataclass, field
from pathlib import Path
from entity import BaseEntity

@dataclass
class AppConfig(BaseEntity):
    silentMode: bool = False
    autoUpdate: bool = False
    unlimitLaunchGame: bool = False

@dataclass
class DownloadConfig(BaseEntity):
    # These fields are for the binary IPC CLI but are managed by Core/GameConfig
    originVersion: str = ""
    targetVersion: str = ""
    
    # Internal settings for IPC
    subport: int = 32568
    pubport: int = 32569
    env: str = "dev"
    oversea: int = 0
    isSSD: int = 1
    rateLimit: int = 0
    isRepairMode: int = 0
    repairListPath: str = ""
    
    def to_save_dict(self):
        return {
            "isSSD": self.isSSD,
            "rateLimit": self.rateLimit
        }

@dataclass
class GameConfig(BaseEntity):
    app_id: int = 81
    content_id: int = 569
    path: str = ""
    running_process: str = ""
    
    def to_save_dict(self):
        return {
            "app_id": self.app_id,
            "content_id": self.content_id,
            "path": self.path,
            "running_process": self.running_process
        }
    
@dataclass       
class ConfigWrapper(BaseEntity):
    _config_path: Path = field(default=Path("config.json"), repr=False)
    appConfig: AppConfig = field(default_factory=AppConfig)
    downloadConfig: DownloadConfig = field(default_factory=DownloadConfig)
    gameConfig: GameConfig = field(default_factory=GameConfig)
    
    @staticmethod
    def load(path: Path = Path("config.json")) -> 'ConfigWrapper':
        config = ConfigWrapper()
        config._config_path = path
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data: dict = json.load(f)
                config.appConfig.update(data.get("appConfig", {}))
                config.downloadConfig.update(data.get("downloadConfig", {}))
                config.gameConfig.update(data.get("gameConfig", {}))
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
        return config
    
    def save(self):
        save_config = {
            "appConfig": self.appConfig.to_save_dict(),
            "downloadConfig": self.downloadConfig.to_save_dict(),
            "gameConfig": self.gameConfig.to_save_dict()
        }
        
        path = getattr(self, "_config_path", Path("config.json"))
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(save_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
