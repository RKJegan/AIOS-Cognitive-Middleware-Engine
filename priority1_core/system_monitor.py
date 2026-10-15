import shutil
import time
import psutil
from core.logger import get_logger
from core.narrator import narrate

log = get_logger()


class SystemMonitor:
    def _all_disks(self):
        disks = {}
        for part in psutil.disk_partitions(all=False):
            drive = part.mountpoint.rstrip("\\").rstrip("/")
            try:
                u = shutil.disk_usage(part.mountpoint)
                disks[drive] = {"free_gb": round(u.free / 1024**3, 1), "total_gb": round(u.total / 1024**3, 1),
                                "used_percent": round(u.used / u.total * 100, 1)}
            except (PermissionError, OSError):
                continue
        return disks

    def get_status(self):
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        net = psutil.net_io_counters()
        data = {
            "cpu_percent": cpu, "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / 1024**3, 1), "ram_total_gb": round(mem.total / 1024**3, 1),
            "disks": self._all_disks(), "battery_percent": battery.percent if battery else None,
            "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1),
            "process_count": len(psutil.pids()),
            "network_sent_mb": round(net.bytes_sent / 1024**2, 1), "network_recv_mb": round(net.bytes_recv / 1024**2, 1),
        }
        return {"status": "success", "message": "System status retrieved", "data": data}

    def get_single_stat(self, stat):
        data = self.get_status()["data"]
        stat_map = {
            "cpu": ("cpu_percent", "CPU usage is {}%"), "ram": ("ram_percent", "RAM usage is {}%"),
            "memory": ("ram_percent", "RAM usage is {}%"), "battery": ("battery_percent", "Battery is at {}%"),
            "uptime": ("uptime_hours", "Up for {} hours"), "processes": ("process_count", "{} processes running"),
        }
        if stat in stat_map:
            key, template = stat_map[stat]
            value = data.get(key)
            if value is None:
                narrate(f"No {stat} info available")
                return {"status": "not_found", "message": f"No data for '{stat}'", "data": None}
            msg = template.format(value)
            narrate(msg)
            return {"status": "success", "message": msg, "data": {stat: value}}

        drive_key = stat.upper().rstrip(":") + ":"
        if drive_key in data["disks"]:
            d = data["disks"][drive_key]
            msg = f"{drive_key} has {d['free_gb']} GB free of {d['total_gb']} GB"
            narrate(msg)
            return {"status": "success", "message": msg, "data": {drive_key: d}}

        narrate("Here's the full status")
        return {"status": "success", "message": "Full status (stat not recognized)", "data": data}

    def get_top_processes(self, limit=5):
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        top = sorted(procs, key=lambda x: x.get("cpu_percent") or 0, reverse=True)[:limit]
        narrate("Top processes: " + ", ".join(p["name"] for p in top if p.get("name")))
        return {"status": "success", "message": f"Top {limit} processes", "data": top}

    def handle(self, intent):
        action = intent.get("action")
        name = intent.get("name")
        if action == "top_processes":
            return self.get_top_processes()
        if action == "status" and name:
            return self.get_single_stat(name.lower().strip())
        if action == "status":
            return self.get_status()
        return {"status": "unhandled", "message": f"System action '{action}' not implemented yet", "data": None}
