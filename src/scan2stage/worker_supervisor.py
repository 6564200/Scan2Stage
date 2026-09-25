from __future__ import annotations

import sys
import traceback

from .storage import Store, utcnow


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scan2stage.worker_supervisor RUN_ID")

    run_id = sys.argv[1]
    store = Store()
    log_path = store.log_path(run_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Import the heavy worker inside the guarded section. This is deliberate:
        # syntax/import/dependency errors must still transition the Run out of
        # queued/running state.
        from .worker import run_job

        code = int(run_job(run_id))
        raise SystemExit(code)
    except SystemExit:
        raise
    except BaseException:
        with log_path.open("a", encoding="utf-8") as log:
            log.write("\n=== worker supervisor failure ===\n")
            traceback.print_exc(file=log)

        run = store.run(run_id)
        if run and run["status"] in {"queued", "running"}:
            store.update_run(
                run_id,
                status="failed",
                message="Worker не запустился — см. логи",
                finished_at=utcnow(),
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
