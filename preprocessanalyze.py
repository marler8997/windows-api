from enum import Enum

class DefineStateKind(Enum):
    QUANTUM = 0
    DEFINED = 1
    NOT_DEFINED = 2
class DefineState:
    def __init__(self, id, kind, value):
        self.id = id
        self.kind = kind
        self.value = value
