import csv
from typing import List

from rlox_app_tracker.data.models import AppStats
from rlox_app_tracker.data.repository import Repository


class Reporter:
    def __init__(self, repo: Repository):
        self.repo = repo

    def get_daily_stats(self) -> List[AppStats]:
        return self.repo.get_stats(period_days=1)

    def get_weekly_stats(self) -> List[AppStats]:
        return self.repo.get_stats(period_days=7)

    def get_monthly_stats(self) -> List[AppStats]:
        return self.repo.get_stats(period_days=30)

    def get_all_time_stats(self) -> List[AppStats]:
        return self.repo.get_stats(period_days=None)

    @staticmethod
    def export_csv(stats: List[AppStats], path: str):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Приложение", "Процесс",
                        "Активное (сек)", "Фоновое (сек)", "Сессий"])
            for s in stats:
                w.writerow([
                    s.display_name or s.process_name,
                    s.process_name,
                    s.active_seconds,
                    s.background_seconds,
                    s.session_count,
                ])
