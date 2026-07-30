import argparse
import logging
from objects.config import Config
from rich.console import Console
from types import SimpleNamespace
from telethon.types import User, Chat, Channel

logger = logging.getLogger(__name__)


def format_eta(seconds: float) -> str:
    """
    A function that makes the estimated remaining time in a nice format.

    Args:
        seconds (float):
            The amount of seconds that will be converted into a nicely formatted string.

    Returns:
        str:
            The ETA in a nice format, Ex:
                `1d 4h 40m 3s`
                `3h 0m 8s`
                `10s`
    """

    # While the provided time is a float, which is usually the case for time
    # related values, we need it to be an int, because the math will not work otherwise.
    seconds = int(seconds)

    d: int = seconds // (3600 * 24)
    h: int = (seconds % (3600 * 24)) // 3600
    m: int = (seconds % 3600) // 60
    s: int = seconds % 60

    if d:
        return f"{d}d {h}h {m}m {s}s"
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def clear_last_line(number_of_lines: int = 1):
    """
    Removes the last line in the command prompt.

    Args:
        number_of_lines (int):
            The number of lines you want to remove from the command line, default=1.
    """

    for _ in range(number_of_lines):
        print("\033[F\033[K", end="")


def parse_args(config: Config) -> None:
    """
    A helper function that parses the configuration of archiving
    from user in CLI.

    Args:
        config (objects.config.Config):
            The config object which has the settings the user
            has provided.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--archive-all", action="store_true", help="archive everything"
    )
    parser.add_argument(
        "-t",
        "--archive-text",
        action="store_true",
        help="archive text messages (including forward, reply, edit, and sender_id)",
    )
    parser.add_argument(
        "-r",
        "--archive-reactions",
        action="store_true",
        help="archive message reactions",
    )
    parser.add_argument(
        "-d",
        "--archive-dialog-info",
        action="store_true",
        help="archive dialog info like title, bio, pfps, and etc.",
    )
    parser.add_argument(
        "-u",
        "--archive-user-info",
        action="store_true",
        help="archive info of users in a dialog, like name, bio, pfps, and etc.",
    )
    parser.add_argument(
        "-f",
        "--archive-file",
        action="store_true",
        help="archive files, like photos, videos, documents, and etc. with a size threshold (default: 100MB)",
    )
    parser.add_argument(
        "-b",
        "--archive-big-files",
        action="store_true",
        help="archive all files ignoring the default of 100MB",
    )
    parser.add_argument(
        "-s",
        "--size-threshold",
        default=100,
        type=int,
        metavar="MB",
        help="the size threshold for files (default: 100MB)",
    )

    args = parser.parse_args()

    # If the user wants to archive everything
    if args.archive_all:
        config.texts = True
        config.reactions = True
        config.dialog_metadata = True
        config.user_metadata = True
        config.files = True
        config.size_threshold = float("inf")

    # If the user doesn't want to archive everything
    else:
        config.texts = args.archive_text
        config.reactions = args.archive_reactions
        config.dialog_metadata = args.archive_dialog_info
        config.user_metadata = args.archive_user_info
        config.files = args.archive_file

        # If big files are toggled on means no size limit is needed
        if args.archive_big_files:
            config.files = True
            config.size_threshold = float("inf")

        # If files only are toggled we expect some size limit to be provided
        # the default is 100MB, so it is not a must.
        elif args.archive_file:
            config.files = True
            config.size_threshold = args.size_threshold * (1024**2)

        # Save only file metadata, don't download files.
        elif args.archive_text:
            config.files = True
            config.size_threshold = 0

        else:
            config.files = False
            config.size_threshold = args.size_threshold * (1024**2)


def byte_to_mb(size: int) -> float:
    """A helper function that converts bytes to megabytes."""
    return (size / 1024) / 1024


def mb_to_byte(size: float) -> int:
    """A helper function that converts megabytes to bytes."""
    return size * 1024**2


def print_three_dialogs(l: list, i: int, con: Console) -> None:
    """
    A function that takes the list of dialogs, and prints three or less dialogs
    for the user as a UI to navigate through.

    Args:
        dialogs (list):
            A list of the dialogs.

        i (int):
            The current dialog's index.

        console (rich.console.Console):
            The object which we will use to print things.
    """

    FIRST_LINE = """
        Do you want to archive the highlighted dialog?
        press [green]y[/] or [green]Enter[/] for yes, 
        [red]q[/] to exit, 
        [cyan]arrow keys[/] to navigate
        and [yellow]i[/] to input a dialog yourself\n"""

    # If there's not dialog
    if len(l) == 0:
        con.print("There's no dialog to work with.\n")
        return

    # If there's one dialog
    if len(l) == 1:
        con.print(f"Do you want to archive: {l[0].name}? (y, q to exit)")
        return

    # If there are two dialogs
    if len(l) == 2:
        con.print(
            FIRST_LINE,
            f"> [bold black on cyan]1.{l[0].name}[/]\n",
            f"  2.{l[1].name}\n",
        )
        return

    to_print = []

    # If we are at the first dialog of the dialogs list
    if i == 0:
        to_print = [f"{len(l)}.{l[-1].name}", f"1.{l[0].name}", f"2.{l[1].name}"]

    # If we are at the last dialog of the dialogs list
    elif i + 1 == len(l):
        to_print = [f"{i}.{l[i - 1].name}", f"{i + 1}.{l[i].name}", f"1.{l[0].name}"]

    # If we are not near any boundary of the list
    # i.e. a normal situation
    else:
        to_print = [
            f"{i}.{l[i - 1].name}",
            f"{i + 1}.{l[i].name}",
            f"{i + 2}.{l[i + 1].name}",
        ]

    con.print(
        FIRST_LINE,
        f"  {to_print[0]}\n",
        f"> [bold black on cyan]{to_print[1]}[/]\n",
        f"  {to_print[2]}\n",
    )

    return


def handle_index(i: int, amount: int, list_length: int) -> int:
    """
    A function that handles incrementing, and decrementing
    an index so that it doesn't get out of boundary.

    Args:
        i (int):
            The index one wants to increment.

        amount (int):
            The amount you want to increment or decrement from
            the index.

        list_length (int):
            The length of the list the index is on.

    Returns:
        int:
            The new index.
    """

    # Case: Increment
    if amount == 1:
        # If we are at the last element flip the index
        if i + 1 == list_length:
            return 0

        return i + 1

    # Case: Decrement
    # If we are at the first element flip the index as well
    if i == 0:
        return list_length - 1

    return i - 1


def construct_fake_dialog(entity) -> SimpleNamespace:
    """
    A function that takes a telethon entity and returns an
    object that simulates how dialog works, having the necessary
    things that this program uses only, since you can't get a dialog
    in telethon unless you have chatted with before.

    Args:
        entity:
            The object that you get from client.get_entity().

    Returns:
        SimpleNamespace:
            An object that simulates a fake dialog.
    """

    if isinstance(entity, User):
        name = f"{entity.first_name} {entity.last_name}"
    elif isinstance(entity, (Chat, Channel)):
        name = entity.title
    else:
        logger.error(f"Entity is not a known type: {entity}")
        name = "UNKNOWN TYPE"

    dialog = SimpleNamespace(id=entity.id, name=name, entity=entity)

    return dialog
