from dataclasses import dataclass


@dataclass()
class Config:
    texts: bool = True
    reactions: bool = True
    dialogInfo: bool = True
    userInfo: bool = True
    files: bool = True
    fileSizeThresholdInBytes: int = (1024**2) * 100  # 100 MB

    def __str__(self):
        return f"""
            texts: {self.texts},
            reactions : {self.reactions}
            dialogInfo : {self.dialogInfo}
            userInfo : {self.userInfo}
            files : {self.files}
            fileSizeThresholdInBytes : {self.fileSizeThresholdInBytes}
        """
