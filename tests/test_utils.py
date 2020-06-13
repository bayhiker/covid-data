from collector.utils import (
    get_date_titles,
    get_title_from_yyyymmdd,
    get_title_from_date,
    get_title_tomorrow,
    get_title_yesterday,
    date_range,
)
from datetime import datetime, timedelta


class UtilsTestCase:
    def test_get_date_title(self):
        assert get_date_titles("2/28/20", "3/1/20") == [
            "2/28/20",
            "2/29/20",
            "3/1/20",
        ]

    def test_get_title_tomorrow(self):
        assert get_title_tomorrow("2/29/20") == "3/1/20"

    def test_get_title_yesterday(self):
        assert get_title_yesterday("3/1/20") == "2/29/20"

    def test_date_range(self):
        l = list(date_range(datetime.now(), datetime.now() + timedelta(10)))
        assert len(l) == 10
        l = list(date_range(datetime.now(), datetime.now() + timedelta(-20)))
        assert len(l) == 20

    def test_get_title_from_yyyymmdd(self):
        assert get_title_from_yyyymmdd("20200301") == "3/1/20"
