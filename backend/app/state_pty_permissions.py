"""Apply the narrow, read-only permission boundary to SvxLink's STATE_PTY."""
from __future__ import annotations

import argparse
import grp
import os
import stat
import sys
from pathlib import Path


def bind_permissions(path: Path, group: str = "svxlink-state-reader") -> None:
    """Make one configured PTY/FIFO readable by the collector group.

    SvxLink creates its configured STATE_PTY path as a symlink to a PTY in
    ``/dev/pts``.  Resolve that one link only, and reject anything outside the
    direct ``/dev/pts/<name>`` namespace before changing permissions.  The
    binder is a root service and must never follow an arbitrary symlink.
    The PTY owner retains its existing owner permissions; the reader group gets
    read-only access and no other mode bits are granted.
    """
    info = os.lstat(path)
    target = path
    if stat.S_ISLNK(info.st_mode):
        link_target = os.readlink(path)
        target = Path(link_target)
        if not target.is_absolute() or target.parent != Path("/dev/pts") or not target.name.isdecimal():
            raise ValueError("STATE_PTY symlink must target a direct /dev/pts device")
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    descriptor = os.open(target, flags)
    try:
        info = os.fstat(descriptor)
        if not (stat.S_ISCHR(info.st_mode) or stat.S_ISFIFO(info.st_mode)):
            raise ValueError("STATE_PTY must be a direct character device or FIFO")
        gid = grp.getgrnam(group).gr_gid
        os.fchown(descriptor, -1, gid)
        os.fchmod(descriptor, 0o640)
    finally:
        os.close(descriptor)


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