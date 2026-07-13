import json
import logging
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from rlox_app_tracker.metadata import MANIFEST_URL as UPDATE_URL
from rlox_app_tracker.version import __version_base__

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"


@dataclass
class UpdateInfo:
    version: str
    url: str
    notes: str


@dataclass
class UpdateResult:
    status: UpdateStatus
    info: Optional[UpdateInfo] = None
    error: Optional[str] = None


def _parse_version(v: str) -> tuple:
    v = v.lstrip("v").split("-")[0]
    parts = [int(x) for x in v.split(".") if x.isdigit()]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def check_for_update(timeout: float = 5.0) -> UpdateResult:
    try:
        req = urllib.request.Request(
            UPDATE_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "RusLOXPy",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        latest = data.get("tag_name", "")
        if not latest:
            logger.warning("Update check: пустой tag_name")
            return UpdateResult(status=UpdateStatus.ERROR)
        if _parse_version(latest) > _parse_version(__version_base__):
            return UpdateResult(
                status=UpdateStatus.UPDATE_AVAILABLE,
                info=UpdateInfo(
                    version=latest,
                    url=data.get("html_url", ""),
                    notes=data.get("body", ""),
                ),
            )
        return UpdateResult(status=UpdateStatus.UP_TO_DATE)
    except urllib.error.HTTPError as e:
        logger.warning("Update check HTTP %s: %s", e.code, e.reason)
        return UpdateResult(status=UpdateStatus.ERROR, error=f"HTTP {e.code}")
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as e:
        logger.warning("Update check failed: %s", e)
        return UpdateResult(status=UpdateStatus.ERROR, error=str(e))
    except Exception:
        logger.exception("Update check unexpected error")
        return UpdateResult(status=UpdateStatus.ERROR, error="Неизвестная ошибка")
