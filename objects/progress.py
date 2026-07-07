import time
from helpers.utils import formatETA, clearLastLine


class Progress:
    def __init__(self, totalMessages: int) -> None:
        self.MbToByte: int = 1024**2
        self.sizeInMb: int = 0
        self.timeStart: float = time.perf_counter()
        self.totalMessages: int = totalMessages
        self.totalMessagesPercent: int = max(totalMessages // 100, 1)
        self.messageCounter: int = 1
        self.lastMessageID: int = 1
        self.savedDialogInfo: bool = False

    def useCheckpoint(self, checkpoint: list) -> None:
        if not checkpoint:
            return
        self.lastMessageID = checkpoint[0]
        self.messageCounter = checkpoint[1]
        self.savedDialogInfo = checkpoint[3]
        self.timeStart -= checkpoint[4]

    def update(self, lastMessageID: int) -> None:
        self.messageCounter += 1
        self.lastMessageID = lastMessageID
        self.checkProgress()

    def __str__(self) -> str:
        if self.totalMessages <= 0:
            return "Progress: N/A"

        progressPercent: float = min(
            self.messageCounter / self.totalMessages * 100, 100
        )
        progressInTens: int = int(progressPercent // 10)
        progressBar: str = "█" * progressInTens + "░" * (10 - progressInTens)
        elapsedTime: float = time.perf_counter() - self.timeStart
        ETAElapsed: str = formatETA(elapsedTime)
        messageRate: float = 0.0
        downloadRate: float = 0.0
        remainingTime: float = 0.0

        if elapsedTime > 0:
            messageRate = self.messageCounter / elapsedTime
            messageRateFormatted: str = f"{self.messageCounter / elapsedTime:.3f}msg/s"
            downloadRate = f"{self.sizeInMb / elapsedTime:.3f}MB/s"
            if messageRate > 0:
                remainingTime = (self.totalMessages - self.messageCounter) / messageRate

        ETARemaining: str = formatETA(remainingTime)
        sizeInMBFormatted: str = f"{self.sizeInMb:.3f}MB"

        status = (
            f"Message {self.messageCounter:^14} | "
            f"{ETAElapsed:^14} | "
            f"{sizeInMBFormatted:^8} | "
            f"{messageRateFormatted:^8} | "
            f"{downloadRate:^8} | "
            f"ETA: {ETARemaining:^14}\n"
            f"Progress: {progressBar}..."
        )

        return status

    def checkProgress(self) -> None:
        if self.messageCounter % self.totalMessagesPercent == 0:
            clearLastLine(2)
            print(self)
