from typing import List, Optional

from rlox_app_tracker.data.repository import Repository
from rlox_app_tracker.data.models import WatchedApp


class WatchListManager:
    def __init__(self, repo: Repository):
        self.repo = repo

    def add_app(self, process_name: str, exe_path: str = None, display_name: str = None) -> int:
        app = WatchedApp(
            process_name=process_name,
            display_name=display_name or process_name,
            exe_path=exe_path,
        )
        return self.repo.add_watched_app(app)

    def remove_app(self, app_id: int):
        self.repo.remove_watched_app(app_id)

    def get_all(self) -> List[WatchedApp]:
        return self.repo.get_all_watched_apps()

    def is_watched(self, process_name: str) -> bool:
        return self.repo.is_watched(process_name)

    def get_by_name(self, name: str) -> Optional[WatchedApp]:
        return self.repo.get_watched_app_by_name(name)
