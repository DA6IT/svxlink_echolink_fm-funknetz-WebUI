from __future__ import annotations

import os
import time

from .update_worker_common import (
    STATUS_FILE,
    ensure_dirs,
    read_json,
    write_status,
)

from .update_worker_job import (
    claim,
    process,
)


def main() -> None:
    os.umask(
        0o027
    )

    ensure_dirs()

    last_write = 0.0

    while True:
        request = claim()

        if request:
            if process(
                request
            ):
                time.sleep(1)
                os._exit(75)

        current = (
            time.monotonic()
        )

        if (
            current
            - last_write
            >= 5
        ):
            previous = read_json(
                STATUS_FILE
            )

            job = previous.get(
                "job"
            )

            if not isinstance(
                job,
                dict,
            ):
                job = None

            write_status(
                job
            )

            last_write = current

        time.sleep(1)


if __name__ == "__main__":
    main()
