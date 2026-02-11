from enum import IntEnum


class SendDiagStatus(IntEnum):
    IDLE = 0
    GATHERING = 1
    SENDING = 2
    FAILED = 3
