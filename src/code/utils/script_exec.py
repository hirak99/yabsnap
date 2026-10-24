import asyncio
import contextlib
import os
import subprocess
import tempfile
from collections.abc import Callable, Generator

from .. import global_flags
from . import os_utils


class ScriptExecutionError(Exception):
    """Raised when execution of a generated script fails.

    Attributes:
        cause: The underlying error, typically a CalledProcessError.
        output: Combined stdout/stderr captured so far, joined with newlines.
            Empty when the script ran with inherited stdio, since output then
            went straight to the terminal.
    """

    def __init__(self, cause: Exception, output: str = "") -> None:
        super().__init__(cause)
        self.cause: Exception = cause
        self.output: str = output


@contextlib.contextmanager
def _script_file(contents: str) -> Generator[str]:
    """Writes `contents` to a temporary executable script, yields its path."""
    with tempfile.TemporaryDirectory(prefix="yabsnap_script") as dir:
        temp_file_name = os.path.join(dir, "yabsnap_script.sh")
        with open(temp_file_name, mode="w", encoding="utf_8") as fp:
            fp.write(contents)
        os.chmod(temp_file_name, mode=0o700)
        yield temp_file_name


def execute_sync(contents: str) -> bool:
    """Runs `contents` as a script with inherited stdio.

    Returns:
        True if the script ran, False in dry-run mode (nothing was executed).

    Raises:
        ScriptExecutionError: If the script exits non-zero.
    """
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would execute the script if --dry-run is not passed.")
        return False

    with _script_file(contents) as temp_file_name:
        try:
            subprocess.run(temp_file_name, check=True)
        except subprocess.CalledProcessError as e:
            raise ScriptExecutionError(e) from e
    return True


async def execute_streaming(contents: str, on_output: Callable[[str], None]) -> bool:
    """Runs `contents` as a script, forwarding output lines to `on_output`.

    Unlike execute_sync(), stdio is captured instead of inherited, so a caller
    such as the TUI can present the output instead of having it written to the
    terminal and lost. Lines are forwarded as they arrive, without their
    trailing newline; stderr is merged into stdout.

    The script gets no stdin (it is connected to /dev/null), so it cannot prompt.

    Args:
        contents: The script to run.
        on_output: Called with each output line, as it is produced.

    Returns:
        True if the script ran, False in dry-run mode (nothing was executed).

    Raises:
        ScriptExecutionError: If the script exits non-zero. Its `output`
            attribute holds everything captured.
    """
    if global_flags.FLAGS.dryrun:
        on_output("Would execute the script if --dry-run is not passed.")
        return False

    captured: list[str] = []

    def emit(line: str) -> None:
        captured.append(line)
        on_output(line)

    with _script_file(contents) as temp_file_name:
        proc = await asyncio.create_subprocess_exec(
            temp_file_name,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            emit(raw_line.decode(errors="replace").rstrip("\n"))
        returncode = await proc.wait()

    if returncode != 0:
        output = "\n".join(captured)
        cause = subprocess.CalledProcessError(returncode, temp_file_name, output=output)
        raise ScriptExecutionError(cause, output=output) from cause
    return True
