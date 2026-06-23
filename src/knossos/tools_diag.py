"""Diagnostic tools: health, system_info."""
from __future__ import annotations

import platform
import socket
import subprocess
from datetime import datetime, timezone

from . import __version__, config


def register(mcp) -> None:
    @mcp.tool
    def health() -> dict:
        """Sanity check: service version, hostname, current time, and active allowlist.
        Use this first to confirm the bridge from Machine A to Machine B works."""
        return {
            "service": "knossos",
            "version": __version__,
            "hostname": socket.gethostname(),
            "time": datetime.now(timezone.utc).isoformat(),
            "allowed_dirs": config.ALLOWED_DIRS,
            "allowed_bins": sorted(config.ALLOWED_BINS) or None,
            "delete_enabled": config.ALLOW_DELETE,
        }

    @mcp.tool
    def system_info() -> dict:
        """Report OS, CPU, RAM and GPU (via nvidia-smi when present) of Machine B."""
        info: dict = {
            "os": platform.platform(),
            "python": platform.python_version(),
            "hostname": socket.gethostname(),
            "cpu": platform.processor() or platform.machine(),
        }
        try:
            import psutil
            info["cpu_count"] = psutil.cpu_count(logical=True)
            info["cpu_count_physical"] = psutil.cpu_count(logical=False)
            vm = psutil.virtual_memory()
            info["ram_total"] = vm.total
            info["ram_available"] = vm.available
            info["ram_percent"] = vm.percent
        except Exception as e:  # psutil is best-effort
            info["psutil_error"] = str(e)

        info["gpus"] = _nvidia_smi()
        return info


def _nvidia_smi():
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=10, shell=False,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    gpus = []
    for line in r.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 4:
            gpus.append({
                "name": parts[0],
                "memory_total_mb": parts[1],
                "memory_used_mb": parts[2],
                "utilization_pct": parts[3],
            })
    return gpus
