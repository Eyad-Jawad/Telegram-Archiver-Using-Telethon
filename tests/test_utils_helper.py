import pytest
from helpers.local_utils import *


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
def test_format_ETA(seconds, output):
    assert format_ETA(seconds) == output
