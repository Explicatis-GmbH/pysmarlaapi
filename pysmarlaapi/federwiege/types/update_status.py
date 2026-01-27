from enum import IntEnum


class UpdateStatus(IntEnum):
    IDLE = 0
    DOWNLOADING = 1
    INSTALLING = 2
    FAILED = 3
