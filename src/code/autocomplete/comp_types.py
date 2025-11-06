import enum
import dataclasses


class SpecialCompletion(enum.Enum):
    FILES = "filename"


class CompletionType(enum.Enum):
    COMMAND = 1
    OPTION = 2


@dataclasses.dataclass(frozen=True)
class Completion:
    option: str
    help: str | None
    type: CompletionType


# If it is a single str, it is interpreted as a command.
AllCompletionsT = Completion | SpecialCompletion | str
