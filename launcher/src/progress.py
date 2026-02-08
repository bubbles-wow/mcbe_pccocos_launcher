from dataclasses import dataclass

@dataclass
class DownloadProgress:
    StateFlags: int = -1
    ShowTextKey: str = ""
    ShowDownloadHeadRate: float = 0.0
    ShowDownloadHeadRateStr: str = "0.00 B/s"
    ShowDownloadHeadSize: int = 0
    ShowDownloadHeadPercent: float = 0.0
    ShowDownloadRate: float = 0.0
    ShowDownloadRateStr: str = "0.00 B/s"
    ShowDownloadSize: int = 0
    ShowDownloadPercent: float = 0.0
    ShowBuildRate: float = 0.0
    ShowBuildRateStr: str = "0.00 B/s"
    ShowBuildSize: int = 0
    ShowBuildPercent: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> DownloadProgress:
        return cls(
            StateFlags=data.get("StateFlags", -1),
            ShowTextKey=data.get("ShowTextKey", ""),
            ShowDownloadHeadRate=data.get("ShowDownloadHeadRate", 0.0),
            ShowDownloadHeadRateStr=data.get("ShowDownloadHeadRateStr", "0.00 B/s"),
            ShowDownloadHeadSize=data.get("ShowDownloadHeadSize", 0),
            ShowDownloadHeadPercent=data.get("ShowDownloadHeadPercent", 0.0),
            ShowDownloadRate=data.get("ShowDownloadRate", 0.0),
            ShowDownloadRateStr=data.get("ShowDownloadRateStr", "0.00 B/s"),
            ShowDownloadSize=data.get("ShowDownloadSize", 0),
            ShowDownloadPercent=data.get("ShowDownloadPercent", 0.0),
            ShowBuildRate=data.get("ShowBuildRate", 0.0),
            ShowBuildRateStr=data.get("ShowBuildRateStr", "0.00 B/s"),
            ShowBuildSize=data.get("ShowBuildSize", 0),
            ShowBuildPercent=data.get("ShowBuildPercent", 0.0)
        )