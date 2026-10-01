"""Reproducible RC9 private-beta operational and memory benchmark.

Seeds only synthetic projects, records bounded author-workspace timings, then
purges by the exact project id. Temporary backup archives are removed with the
temporary directory. The normal project library is never selected by title.
"""
from __future__ import annotations

import asyncio
import ctypes
import importlib.util
import json
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.services.project_backup_service import project_backup_service  # noqa: E402
from app.services.project_lifecycle_service import project_lifecycle_service  # noqa: E402
from app.services.workspace_bootstrap_service import workspace_bootstrap_service  # noqa: E402
from app.services.writing_experience_service import writing_experience_service  # noqa: E402


def _load_rc8_helpers():
    path = ROOT / "scripts" / "run_rc8_launch_benchmarks.py"
    spec = importlib.util.spec_from_file_location("rc8_benchmark_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("RC8 benchmark helpers are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = _load_rc8_helpers()
SIZES = (50, 100, 250, 500, 1000)


def working_set_mb():
    value = helpers.working_set_mb()
    if value is not None:
        return value
    if sys.platform == "win32":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        get_current_process = ctypes.windll.kernel32.GetCurrentProcess
        get_current_process.restype = ctypes.c_void_p
        get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        get_memory.restype = ctypes.c_int
        handle = get_current_process()
        if get_memory(handle, ctypes.byref(counters), counters.cb):
            return round(counters.WorkingSetSize / 1024 / 1024, 2)
    return None


async def median_ms(call, repeats: int = 1):
    samples = []
    value = None
    for _ in range(repeats):
        started = time.perf_counter()
        value = await call()
        samples.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(samples), 2), value


async def main() -> None:
    original_backup_directory = settings.backup_directory
    await Database.connect()
    db = Database.get_db()
    results = []
    idle_mb = working_set_mb()
    try:
        with tempfile.TemporaryDirectory(prefix="novelforge-rc9-benchmark-") as temp_dir:
            settings.backup_directory = str(Path(temp_dir) / "backups")
            for size in SIZES:
                project_object_id, project_id = await helpers.seed(db, size)
                before_mb = working_set_mb()
                try:
                    await workspace_bootstrap_service.invalidate(db, project_id)
                    cold_ms, cold = await median_ms(lambda: workspace_bootstrap_service.get(db, project_id))
                    warm_ms, warm = await median_ms(lambda: workspace_bootstrap_service.get(db, project_id), 5)
                    desk_ms, _dashboard = await median_ms(lambda: writing_experience_service.dashboard(db, project_id), 3)
                    after_bootstrap_mb = working_set_mb()

                    # Repeated warm reads approximate the polling/bootstrap pressure of
                    # a long open session without modifying author state.
                    session_before_mb = working_set_mb()
                    session_samples = []
                    for _ in range(30):
                        elapsed, _ = await median_ms(lambda: workspace_bootstrap_service.get(db, project_id))
                        session_samples.append(elapsed)
                    session_after_mb = working_set_mb()

                    backup_ms = None
                    backup_bytes = None
                    if size in (50, 500):
                        backup_ms, backup = await median_ms(
                            lambda: project_backup_service.create(db, project_object_id, reason="RC9 benchmark")
                        )
                        validation_ms, validation = await median_ms(
                            lambda: project_backup_service.validate(db, backup["backup_id"])
                        )
                        backup_bytes = backup["archive_bytes"]
                        await db.project_backups.delete_one({"backup_id": backup["backup_id"]})
                    else:
                        validation_ms = None
                        validation = None

                    results.append({
                        "chapters": size,
                        "classification": "normal_author" if size == 50 else "launch_target",
                        "workspace_bootstrap_cold_ms": cold_ms,
                        "workspace_bootstrap_warm_median_ms": warm_ms,
                        "workspace_cache_hit": bool(warm.get("cache", {}).get("hit")),
                        "workspace_stages_ms": cold.get("performance", {}),
                        "writing_dashboard_median_ms": desk_ms,
                        "thirty_warm_reads_median_ms": round(statistics.median(session_samples), 2),
                        "backup_ms": backup_ms,
                        "backup_validation_ms": validation_ms,
                        "backup_bytes": backup_bytes,
                        "backup_valid": validation.get("valid") if validation else None,
                        "working_set_before_mb": before_mb,
                        "working_set_after_bootstrap_mb": after_bootstrap_mb,
                        "long_session_before_mb": session_before_mb,
                        "long_session_after_mb": session_after_mb,
                        "long_session_delta_mb": (
                            round(session_after_mb - session_before_mb, 2)
                            if session_before_mb is not None and session_after_mb is not None
                            else None
                        ),
                    })
                finally:
                    await project_lifecycle_service.purge(db, project_object_id)
                    await db.project_backups.delete_many({"project_id": project_object_id})
        report = {
            "generated_at_utc": datetime.utcnow().isoformat() + "Z",
            "database": db.name,
            "idle_process_working_set_mb": idle_mb,
            "exact_project_cleanup": True,
            "results": results,
        }
        output = ROOT / "artifacts" / "rc9-operational-performance.json"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        settings.backup_directory = original_backup_directory
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
