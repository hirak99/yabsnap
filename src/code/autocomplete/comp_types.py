import enum
import dataclasses


class CompletionType(enum.Enum):
    COMMAND = 1
    OPTION = 2


# In the future, can add stuff such as extension.
@dataclasses.dataclass(frozen=True)
class FileCompletion:
    pass


@dataclasses.dataclass(frozen=True)
class Completion:
    option: str
    help: str | None
    type: CompletionType


# If it is a single str, it is interpreted as a command.
AllCompletionsT = Completion | FileCompletion | str
