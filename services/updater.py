import json
import logging
import urllib.request
from dataclasses import dataclass
from typing import Optional

from version import __version_base__, UPDATE_URL

logger = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    version: str
    url: str
    notes: str


def _parse_version(v: str) -> tuple:
    v = v.lstrip("v").split("-")[0]
    parts = [int(x) for x in v.split(".") if x.isdigit()]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def check_for_update(timeout: float = 5.0) -> Optional[UpdateInfo]:
    try:
        req = urllib.request.Request(
            UPDATE_URL, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        latest = data.get("tag_name", "")
        if not latest:
            return None
        if _parse_version(latest) > _parse_version(__version_base__):
            return UpdateInfo(
                version=latest,
                url=data.get("html_url", ""),
                notes=data.get("body", ""),
            )
    except Exception:
        logger.warning("Update check failed", exc_info=True)
        return None
    return None
