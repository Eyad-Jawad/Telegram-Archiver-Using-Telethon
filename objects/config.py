from dataclasses import dataclass


@dataclass()
class Config:
    texts: bool = True
    reactions: bool = True
    dialog_metadata: bool = True
    user_metadata: bool = True
    files: bool = True
    size_threshold: int = (1024**2) * 100  # file size threshold in bytes (default: 100 MB)

    def __str__(self):
        return f"""
            texts: {self.texts},
            reactions : {self.reactions}
            dialog_metadata : {self.dialog_metadata}
            user_metadata : {self.user_metadata}
            files : {self.files}
            size_threshold : {self.size_threshold}
        """
