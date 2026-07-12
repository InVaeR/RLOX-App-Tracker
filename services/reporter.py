from typing import List

from data.repository import Repository
from data.models import AppStats


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
