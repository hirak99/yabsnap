import os
import subprocess


def get_version() -> str:
    """Return version string like 'v2.4.2' or 'v2.4.2 r2.g0624f6f'."""
    # Try git describe first (for development/installed-from-git builds).
    try:
        out = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=7", "--dirty"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return f"{out.stdout.strip()} (git)"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    # Fall back to .version file (for packaged releases).
    version_file = ".version"
    if os.path.isfile(version_file):
        try:
            with open(version_file) as f:
                return f.read().strip()
        except OSError:
            pass
    return "v0.0.0 (unknown)"
