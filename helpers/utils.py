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
