from unittest.mock import MagicMock

import pytest
from telethon.types import Channel, Chat, User

from helpers.local_utils import *
from objects.config import Config


@pytest.mark.parametrize(
    ("seconds, output"),
    [
        [0.0, "0s"],
        [10.0, "10s"],
        [60.0, "1m 0s"],
        [61.0, "1m 1s"],
        [300.0, "5m 0s"],
        [3666.0, "1h 1m 6s"],
        [500_000.0, "5d 18h 53m 20s"],
    ],
)
def test_format_eta(seconds, output):
    assert format_eta(seconds) == output


@pytest.mark.parametrize(
    (
        "args, texts, reactions, dialog_metadata, user_metadata, stickers, files, size_threshold"
    ),
    [
        [[], False, False, False, False, False, False, 0],
        [["--archive-all"], True, True, True, True, True, True, float("inf")],
        [["-a"], True, True, True, True, True, True, float("inf")],
        [["--archive-text"], True, False, False, False, False, True, 0],
        [["-t"], True, False, False, False, False, True, 0],
        [["--archive-reactions"], False, True, False, False, False, False, 0],
        [["-r"], False, True, False, False, False, False, 0],
        [["--archive-dialog-info"], False, False, True, False, False, False, 0],
        [["-d"], False, False, True, False, False, False, 0],
        [["--archive-user-info"], False, False, False, True, False, False, 0],
        [["-u"], False, False, False, True, False, False, 0],
        [
            ["--archive-stickers-info"],
            False,
            False,
            False,
            False,
            True,
            False,
            0,
        ],
        [["-k"], False, False, False, False, True, False, 0],
        [
            ["--archive-file"],
            False,
            False,
            False,
            False,
            False,
            True,
            104_857_600,
        ],
        [["-f"], False, False, False, False, False, True, 104_857_600],
        [
            ["--archive-big-files"],
            False,
            False,
            False,
            False,
            False,
            True,
            float("inf"),
        ],
        [["-b"], False, False, False, False, False, True, float("inf")],
        [
            ["-f", "--size-threshold", "1"],
            False,
            False,
            False,
            False,
            False,
            True,
            1_048_576,
        ],
        [["-f", "-s", "1"], False, False, False, False, False, True, 1_048_576],
        [
            ["-f", "--size-threshold", "10"],
            False,
            False,
            False,
            False,
            False,
            True,
            10_485_760,
        ],
        [
            ["-f", "-s", "10"],
            False,
            False,
            False,
            False,
            False,
            True,
            10_485_760,
        ],
        [
            ["-f", "--size-threshold", "1000"],
            False,
            False,
            False,
            False,
            False,
            True,
            1_048_576_000,
        ],
        [
            ["-f", "-s", "1000"],
            False,
            False,
            False,
            False,
            False,
            True,
            1_048_576_000,
        ],
        [
            ["-t", "--archive-dialog-info", "-f"],
            True,
            False,
            True,
            False,
            False,
            True,
            104_857_600,
        ],
        [["-u", "-r"], False, True, False, True, False, False, 0],
    ],
)
def test_parse_agrs(
    args,
    texts,
    reactions,
    dialog_metadata,
    user_metadata,
    stickers,
    files,
    size_threshold,
):
    config = Config()
    parse_args(config, args)

    assert config.texts == texts
    assert config.reactions == reactions
    assert config.dialog_metadata == dialog_metadata
    assert config.user_metadata == user_metadata
    assert config.stickers == stickers
    assert config.files == files
    assert config.size_threshold == size_threshold


@pytest.mark.parametrize(
    ("size, output"),
    [
        [0, 0],
        [1, 9.5367431640625e-07],
        [1_024, 0.0009765625],
        [1_000_000_000, 953.67431640625],
    ],
)
def test_byte_to_mb(size, output):
    assert byte_to_mb(size) == output


@pytest.mark.parametrize(
    ("size, output"),
    [
        [0, 0],
        [1, 1_048_576],
        [1_024, 1_073_741_824],
        [1_000_000_000, 1_048_576_000_000_000],
    ],
)
def test_mb_to_byte(size, output):
    assert mb_to_byte(size) == output


def test_print_three_dialog_with_empty_list():
    console = MagicMock()
    print_three_dialogs([], 0, console)

    console.print.assert_called_once_with(
        "There's no dialog to work with, do you want to input your own dialog? (i)\n"
    )


def test_print_three_dialog_with_length_one_list():
    console = MagicMock()
    dialog = MagicMock()
    dialog.name = "Goodies"
    print_three_dialogs([dialog], 0, console)

    console.print.assert_called_once_with(
        "Do you want to archive: Goodies? (y, q to exit, i to input your own dialog)"
    )


def get_print_three_dialog_first_line():
    return """
        Do you want to archive the highlighted dialog?
        press [green]y[/] or [green]Enter[/] for yes, 
        [red]q[/] to exit, 
        [cyan]arrow keys[/] to navigate
        and [yellow]i[/] to input a dialog yourself\n"""


def make_dialogs_list(*names):
    l = []

    for name in names:
        dialog = MagicMock()
        dialog.name = name
        l.append(dialog)

    return l


def test_print_three_dialog_with_length_two_list():
    console = MagicMock()
    dialogs = make_dialogs_list("Noice", "Good guy")
    FIRST_LINE = get_print_three_dialog_first_line()
    print_three_dialogs(dialogs, 0, console)

    console.print.assert_called_once_with(
        FIRST_LINE, "> [bold black on cyan]1.Noice[/]\n", "  2.Good guy\n"
    )


def test_print_three_dialog_with_length_three_list_from_middle():
    console = MagicMock()
    dialogs = make_dialogs_list("Noice", "Good guy", "Teeth")
    FIRST_LINE = get_print_three_dialog_first_line()
    print_three_dialogs(dialogs, 1, console)

    console.print.assert_called_once_with(
        FIRST_LINE,
        "  1.Noice\n",
        "> [bold black on cyan]2.Good guy[/]\n",
        "  3.Teeth\n",
    )


def test_print_three_dialog_with_length_four_list_from_start():
    console = MagicMock()
    dialogs = make_dialogs_list("Noice", "Good guy", "Teeth", "Battery")
    print(dialogs)
    FIRST_LINE = get_print_three_dialog_first_line()
    print_three_dialogs(dialogs, 0, console)

    console.print.assert_called_once_with(
        FIRST_LINE,
        "  4.Battery\n",
        "> [bold black on cyan]1.Noice[/]\n",
        "  2.Good guy\n",
    )


def test_print_three_dialog_with_length_four_list_from_end():
    console = MagicMock()
    dialogs = make_dialogs_list("Noice", "Good guy", "Teeth", "Battery")
    FIRST_LINE = get_print_three_dialog_first_line()
    print_three_dialogs(dialogs, 3, console)

    console.print.assert_called_once_with(
        FIRST_LINE,
        "  3.Teeth\n",
        "> [bold black on cyan]4.Battery[/]\n",
        "  1.Noice\n",
    )


@pytest.mark.parametrize(
    ("index, amount, output"),
    [
        [0, 1, 1],
        [1, 1, 2],
        [2, 1, 0],
        [0, -1, 2],
        [1, -1, 0],
        [0, 10, 1],
        [1, -10, 0],
    ],
)
def test_handle_index(index, amount, output):
    assert handle_index(index, amount, 3) == output


def test_construct_fake_dialog_with_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.first_name = "Eyad"
    user.last_name = "Also Eyad"

    dialog = construct_fake_dialog(user)

    assert dialog.name == "Eyad Also Eyad"
    assert dialog.id == 1
    assert dialog.entity == user


def test_construct_fake_dialog_with_user_no_last_name():
    user = MagicMock(spec=User)
    user.id = 1
    user.first_name = "Eyad"
    user.last_name = None

    dialog = construct_fake_dialog(user)

    assert dialog.name == "Eyad"
    assert dialog.id == 1
    assert dialog.entity == user


@pytest.mark.parametrize(
    ("type"),
    [Channel, Chat],
)
def test_construct_fake_dialog_with_chat_or_channel(type):
    entity = MagicMock(spec=type)
    entity.id = 1
    entity.title = "Eyad (as well)"

    dialog = construct_fake_dialog(entity)

    assert dialog.name == "Eyad (as well)"
    assert dialog.id == 1
    assert dialog.entity == entity


def test_construct_fake_dialog_with_unknown_type():
    entity = MagicMock()
    entity.id = 1

    dialog = construct_fake_dialog(entity)

    assert dialog.name == "UNKNOWN TYPE"
    assert dialog.id == 1
    assert dialog.entity == entity
