from typing import Dict

import psutil


def list_running_apps() -> Dict[str, str]:
    apps = {}
    for p in psutil.process_iter(["name", "exe"]):
        try:
            name = p.info["name"]
            exe = p.info["exe"]
            if name and exe:
                apps[name] = exe
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return apps
