from typing import Dict, Set

import psutil


def get_running_process_names() -> Set[str]:
    names: Set[str] = set()
    for p in psutil.process_iter(["name"]):
        try:
            if p.info["name"]:
                names.add(p.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return names


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
