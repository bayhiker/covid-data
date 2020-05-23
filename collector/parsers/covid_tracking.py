#
# This parser adds the following data fields to self.data:
# self.data["US"]["0"]["testing"]["settled_cases"]
# self.data["US"]["0"]["testing"]["positive_rate"]
# self.data["US"]["0"]["testing"]["pending_cases"]
# Each of the above three are a dict of [date_label][state_fips]=state_data_for_date
#  and ["time_series"][date_label]=us_data_for_date
#
# Data from covidtracking.com, github COVID19Tracking/covid-tracking-data
# Per https://covidtracking.com/data, the ICU and hospitalization data
# are sparse, highly caveated and should not be used for nation-wide stats.
# State ICU and hospitalization data, however, can still be shown when available
import math
from .covid_parser import CovidParser
from ..utils import get_title_from_date, get_title_from_yyyymmdd
from ..us import state_fips_map


class CovidTrackingParser(CovidParser):
    def __init__(self, data, data_source_folder):
        super().__init__(data, data_source_folder)
        self.source_file_us = (
            f"{data_source_folder}/covid-tracking-data/data/us_daily.csv"
        )
        self.source_file_us_states = (
            f"{data_source_folder}/covid-tracking-data/data/states_daily_4pm_et.csv"
        )
        self.headers_us = []
        self.headers_us_states = []

    def _parse_data_line(self, data_line, headers):
        return dict(zip(headers, self.partition_csv_line(data_line),))

    def _process_csv(self, source_file, header_line_handler, data_line_handler):
        with open(source_file) as fp:
            data_line = fp.readline()
            header_line_handler(data_line)
            while data_line:
                data_line = fp.readline()
                data_line_handler(data_line)

    def _parse_header_us(self, header_line):
        self.headers_us = self.partition_csv_line(header_line)

    def _handle_data_line_us(self, data_line):
        d = self._parse_data_line(data_line, self.headers_us)
        if not "date" in d:
            print(f"No date in line '{data_line}'', skiping")
            return
        (settled_cases, positive_rate, pending_cases) = _extract_testing_data(d)
        date_label = get_title_from_yyyymmdd(d["date"])
        us_settled_cases_ts = self.get_data_us_settled_cases_ts()
        us_settled_cases_ts[date_label] = settled_cases
        us_positive_rate_ts = self.get_data_us_positive_rate_ts()
        us_positive_rate_ts[date_label] = positive_rate
        us_pending_cases_ts = self.get_data_us_pending_cases_ts()
        us_pending_cases_ts[date_label] = pending_cases

    def _parse_header_us_states(self, header_line):
        self.headers_us_states = self.partition_csv_line(header_line)

    def _handle_data_line_us_states(self, data_line):
        d = self._parse_data_line(data_line, self.headers_us_states)
        if not "date" in d:
            print(f"No date in line '{data_line}', skiping")
            return
        if "state" not in d:
            print(f"No state info in line '{data_line}', skiping")
            print(f"d was !{d}!")
            return
        if d["state"] not in state_fips_map:
            print(f"No such state in state_fips_map: {d['state']}")
            return
        state_fips = state_fips_map[d["state"]]
        (settled_cases, positive_rate, pending_cases) = _extract_testing_data(d)
        date_label = get_title_from_yyyymmdd(d["date"])
        state_settled_cases_ts = self.get_data_state_settled_cases_ts(state_fips)
        state_settled_cases_ts[date_label] = settled_cases
        state_positive_rate_ts = self.get_data_state_positive_rate_ts(state_fips)
        state_positive_rate_ts[date_label] = positive_rate
        state_pending_cases_ts = self.get_data_state_pending_cases_ts(state_fips)
        state_pending_cases_ts[date_label] = pending_cases
        us_settled_cases_dl = self.get_data_us_settled_cases_dl(date_label)
        us_settled_cases_dl[state_fips] = settled_cases
        us_positive_rate_dl = self.get_data_us_positive_rate_dl(date_label)
        us_positive_rate_dl[state_fips] = positive_rate
        us_pending_cases_dl = self.get_data_us_pending_cases_dl(date_label)
        us_pending_cases_dl[state_fips] = pending_cases

    def _process_csv_us(self):
        self._process_csv(
            self.source_file_us, self._parse_header_us, self._handle_data_line_us
        )

    def _process_csv_us_states(self):
        self._process_csv(
            self.source_file_us_states,
            self._parse_header_us_states,
            self._handle_data_line_us_states,
        )

    def parse(self):
        self._process_csv_us()
        self._process_csv_us_states()

    def get_data_state_settled_cases_ts(self, fips):
        return self.get_data_state_time_series(fips, ["testing", "settled_cases"])

    def get_data_state_settled_cases_dl(self, fips, date_label):
        return self.get_data_state_date_label(
            fips, ["testing", "settled_cases"], date_label
        )

    def get_data_us_settled_cases_ts(self):
        return self.get_data_us_time_series(["testing", "settled_cases"])

    def get_data_us_settled_cases_dl(self, date_label):
        return self.get_data_us_date_label(["testing", "settled_cases"], date_label)

    def get_data_state_pending_cases_ts(self, fips):
        return self.get_data_state_time_series(fips, ["testing", "pending_cases"])

    def get_data_state_pending_cases_dl(self, fips, date_label):
        return self.get_data_state_date_label(
            fips, ["testing", "pending_cases"], date_label
        )

    def get_data_us_pending_cases_ts(self):
        return self.get_data_us_time_series(["testing", "pending_cases"])

    def get_data_us_pending_cases_dl(self, date_label):
        return self.get_data_us_date_label(["testing", "pending_cases"], date_label)

    def get_data_state_positive_rate_ts(self, fips):
        return self.get_data_state_time_series(fips, ["testing", "positive_rate"])

    def get_data_state_positive_rate_dl(self, fips):
        return self.get_data_state_date_label(fips, ["testing", "positive_rate"])

    def get_data_us_positive_rate_ts(self):
        return self.get_data_us_time_series(["testing", "positive_rate"])

    def get_data_us_positive_rate_dl(self, date_label):
        return self.get_data_us_date_label(["testing", "positive_rate"], date_label)


def _extract_testing_data(d):
    positive = int(d["positive"]) if "positive" in d and d["positive"] != "" else 0
    negative = int(d["negative"]) if "negative" in d and d["negative"] != "" else 0
    pending_cases = int(d["pending"]) if "pending" in d and d["pending"] != "" else 0
    settled_cases = positive + negative
    positive_rate = (
        math.floor(10000 * positive / settled_cases) if settled_cases > 0 else 0
    ) / 100
    return (settled_cases, positive_rate, pending_cases)
