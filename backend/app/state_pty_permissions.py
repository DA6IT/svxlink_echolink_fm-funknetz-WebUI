"""Apply the narrow, read-only permission boundary to SvxLink's STATE_PTY."""
from __future__ import annotations

import argparse
import grp
import os
import stat
import sys
from pathlib import Path


def bind_permissions(path: Path, group: str = "svxlink-state-reader") -> None:
    """Make one directly configured PTY/FIFO readable by the collector group.

    The path is deliberately not followed through a symlink: the binder is a
    root service and must never be tricked into changing an unrelated file.
    The PTY owner retains its existing owner permissions; the reader group gets
    read-only access and no other mode bits are granted.
    """
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or not (stat.S_ISCHR(info.st_mode) or stat.S_ISFIFO(info.st_mode)):
        raise ValueError("STATE_PTY must be a direct character device or FIFO")
    gid = grp.getgrnam(group).gr_gid
    os.chown(path, -1, gid)
    os.chmod(path, 0o640)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind restrictive STATE_PTY permissions")
    parser.add_argument("path", type=Path)
    parser.add_argument("--group", default="svxlink-state-reader")
    args = parser.parse_args()
    try:
        bind_permissions(args.path, args.group)
    except (FileNotFoundError, PermissionError, OSError, ValueError, KeyError) as error:
        print(f"STATE_PTY permission binder failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())