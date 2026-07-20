import argparse
from objects.config import Config

def formatETA(seconds: float) -> str:
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


def clearLastLine(numberOfLines=1):
    # It literally removes the last line in the command prompt
    for _ in range(numberOfLines):
        print("\033[F\033[K", end="")


def parseArgs(config: Config) -> None:
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

    if args.archive_all:
        config.texts = True
        config.reactions = True
        config.dialogInfo = True
        config.userInfo = True
        config.files = True
        config.fileSizeThresholdInBytes = float("inf")
    else:
        config.texts = args.archive_text
        config.reactions = args.archive_reactions
        config.dialogInfo = args.archive_dialog_info
        config.userInfo = args.archive_user_info
        config.files = args.archive_file

        if args.archive_big_files:
            config.files = True
            config.fileSizeThresholdInBytes = float("inf")

        elif args.archive_file:
            config.files = True
            config.fileSizeThresholdInBytes = args.size_threshold * (1024**2)

        elif args.archive_text:
            # Save only file metadata, don't download files.
            config.files = True
            config.fileSizeThresholdInBytes = 0

        else:
            config.files = False
            config.fileSizeThresholdInBytes = args.size_threshold * (1024**2)
