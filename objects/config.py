from dataclasses import dataclass


@dataclass()
class Config:
    checkSize: bool = False
    texts: bool = True
    reactions: bool = True
    dialogInfo: bool = True
    userInfo: bool = True
    files: bool = True
    fileSizeThresholdInBytes: int = (1024**2) * 100  # 100 MB
