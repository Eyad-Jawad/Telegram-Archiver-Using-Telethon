import time
import logging
from helpers.local_utils import format_eta, byte_to_mb
from rich.table import Table
from rich.progress_bar import ProgressBar

logger = logging.getLogger(__name__)


class Progress:
    def __init__(self, total_messages: int, dialog_name: str) -> None:
        """
        Initialize the progress class which handles how progress
        is shown in the CLI while archiving a dialog.

        Args:
            total_messages (int):
                The number of total messages of a dialog.

            dialog_name (str):
                The title of the dialog being archived, can be accessed
                through dialog.name.
        """

        logger.info("Setting up the Progress class...")

        self.dialog_name = dialog_name
        self.total_messages: int = total_messages
        self.message_counter: int = 0
        self.last_message_id: int = 1
        self.used_space_in_MB: int = 0
        self.time_start: float = time.perf_counter()

        self.bar = ProgressBar(total_messages, 0, 40)

    def use_checkpoint(self, checkpoint: tuple[int, int, float]) -> None:
        """
        A method that takes archiving progress and updates
        the attributes of the class.

        Args:
            checkpoint (tuple [int, int, float]):
                A tuple of values taken from Dialog.get_checkpoint()
        """

        # Just for safety
        if not checkpoint:
            return

        # Update the attributes
        self.last_message_id = checkpoint[0]
        self.message_counter = checkpoint[1]
        # time_start is different because it is a float of the
        # time it took to archive, that's why we offset the
        # current time by its value.
        self.time_start -= checkpoint[2]

    def update(self, last_message_id: int) -> None:
        """
        A method that updates internal attributes.

        Args:
            last_message_id (int):
                The id of the last message archived. It is not always an increment
                of the last id, that's why it must be provided.
        """

        # For safety
        if not last_message_id:
            return

        if last_message_id <= 0:
            logger.error("Recieved negative message id.")

        self.message_counter += 1
        self.last_message_id = last_message_id
        self.bar.update(self.message_counter)

    def update_file_progress(self, file_size: int) -> None:
        """
        A method that updates attributes having to do with files.

        Args:
            file_size (int):
                The size of the last file downloaded in bytes.
        """

        # For safety
        if not file_size:
            return

        if file_size < 0:
            logger.error("Recived negative file size.")
            return

        self.used_space_in_MB += byte_to_mb(file_size)

    def make_table(self) -> Table:
        """
        A method that returns a table from 'rich' library.

        Returns:
            rich.table.Table:
                A table with the needed columns, and one row for progress.
        """

        # Initilize the table.
        # We do not update it because 'ric`h' tables are not mutable,
        # that's why we need to make a new one each time
        table = Table(title=f"Progress of Archiving {self.dialog_name}")

        table.add_column("Message #", justify="center")
        table.add_column("Remaining messages", justify="center")
        table.add_column("Elapsed time", justify="center")
        table.add_column("ETA", justify="center")
        table.add_column("msg/sec", justify="center")
        table.add_column("Used space (MB)", justify="center")
        table.add_column("MB/sec", justify="center")

        # For safety
        if self.total_messages <= 0:
            table.add_row(0, "0s", "N/A", 0, 0, 0)
            return table

        elapsed_time: float = time.perf_counter() - self.time_start
        msgs_per_sec: float = 0.0
        MB_per_sec: float = 0.0
        remaining_time: float = 0.0

        # For safety
        if elapsed_time > 0:
            msgs_per_sec = self.message_counter / elapsed_time
            MB_per_sec = f"{self.used_space_in_MB / elapsed_time:.3f}MB/s"
            # For safety
            if msgs_per_sec > 0:
                remaining_time = (
                    self.total_messages - self.message_counter
                ) / msgs_per_sec

        # There were three safety checks so we don't divide by 0 by mistake

        table.add_row(
            str(self.message_counter),
            str(self.total_messages - self.message_counter),
            format_eta(elapsed_time),
            format_eta(remaining_time),
            f"{msgs_per_sec:.3f}msg/s",
            f"{self.used_space_in_MB:.3f}MB",
            MB_per_sec,
        )

        return table
