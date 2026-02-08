from dataclasses import dataclass, field, asdict

@dataclass
class GameState:
    Name: str = ""
    AppId: str = "0"
    StateFlag: int = 0
    installed_contents: dict[str, ContentInfo] = field(default_factory=dict)
    staged_contents: dict[str, ContentInfo] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        def parse_contents(content_dict):
            if content_dict is None: return ContentInfo()
            return {
                str(k): ContentInfo(**{nk: nv for nk, nv in v.items() if nk in ContentInfo.__dataclass_fields__})
                for k, v in content_dict.items() if isinstance(v, dict)
            }
        
        return cls(
            Name=data.get("Name", ""),
            AppId=str(data.get("AppId", "0")),
            StateFlag=data.get("StateFlag", 0),
            installed_contents=parse_contents(data.get("installed_contents", {})),
            staged_contents=parse_contents(data.get("staged_contents", {}))
        )

    def get_version(self, content_id: int, staged=False) -> str:
        cid_str = str(content_id)
        contents = self.staged_contents if staged else self.installed_contents
        info = contents.get(cid_str)
        return info.Version if info else ""

@dataclass
class ContentInfo:
    AppContentId: str = ""
    DownloadableId: str = ""
    Version: str = ""
    UseCompatibleGzip: bool = False
    Mode: int = 0
    RepairFiles: list = None

    @classmethod
    def from_dict(cls, data: dict):
        if not data: return None
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})