import argparse
from objects.config import Config


def format_ETA(seconds: float) -> str:
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


def byte_to_MB(size: int) -> float:
    """A helper function that converts bytes to megabytes."""
    return (size / 1024) / 1024


def MB_to_byte(size: float) -> int:
    """A helper function that converts megabytes to bytes."""
    return size * 1024**2
