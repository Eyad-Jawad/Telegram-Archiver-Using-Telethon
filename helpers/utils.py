import json, time

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

def saveCheckpoint (
        lastMessageID: int, 
        messageCounter: int,         
        fileCounter: int, 
        flagOfGetDialogInfo: bool, 
        dialogPath: str, 
        timeStart: float
    ) -> None:
    dialog = []
    try:
        with open(f"{dialogPath}/CheckPoint.json", 'r') as f:
            dialog = json.load(f) 
            # if any of the inputs is 0 means don't change it, like if you haven't parsed the dialog info yet
            if lastMessageID:       dialog[0] = lastMessageID
            if messageCounter:      dialog[1] = messageCounter
            if fileCounter:         dialog[2] = fileCounter
            if flagOfGetDialogInfo: dialog[3] = flagOfGetDialogInfo
            if timeStart:           dialog[4] = time.perf_counter() - timeStart
    except (FileNotFoundError, json.JSONDecodeError):
        dialog = [lastMessageID, messageCounter, fileCounter, flagOfGetDialogInfo, time.perf_counter() - timeStart]
        
    with open(f"{dialogPath}/CheckPoint.json", 'w') as f:
        f.write(json.dumps(dialog))

def getCheckpoint(dialogPath: str) -> list:
    try:
        with open(f"{dialogPath}/CheckPoint.json", 'r') as f:
            dialogs = json.load(f)
            return dialogs
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def clearLastLine(numberOfLines = 1):
    # It literally removes the last line in the command prompt
    for _ in range(numberOfLines):
        print("\033[F\033[K", end='')