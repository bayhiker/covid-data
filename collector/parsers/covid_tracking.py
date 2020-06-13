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
from ..utils import get_title_from_date, get_title_from_yyyymmdd, get_title_yesterday
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
        self.most_recent_date = None
        self.least_recent_date = None

    def parse(self):
        self._process_csv_us()
        self._process_csv_us_states()
        # So far positive_rate fields contain positive_cases, replace with positive_rates
        self._calculate_positive_rates()

    def _parse_data_line(self, data_line, headers):
        return dict(zip(headers, self.partition_csv_line(data_line),))

    def _process_csv(self, source_file, header_line_handler, data_line_handler):
        with open(source_file) as fp:
            header_line = fp.readline()
            header_line_handler(header_line)
            current_line = fp.readline()
            is_first_data_line = True
            date_processed = None
            while current_line:
                date_processed = data_line_handler(current_line)
                if is_first_data_line and not self.most_recent_date:
                    self.most_recent_date = get_title_from_yyyymmdd(date_processed)
                current_line = fp.readline()
            if not self.least_recent_date:
                self.least_recent_date = get_title_from_yyyymmdd(date_processed)

    def _parse_header_us(self, header_line):
        self.headers_us = self.partition_csv_line(header_line)

    def _handle_data_line_us(self, current_line):
        d = self._parse_data_line(current_line, self.headers_us)
        if not "date" in d:
            print(f"No date in line '{current_line}'', skiping")
            return
        (settled_cases, positive_cases, pending_cases) = _extract_testing_data(d)
        date_label = get_title_from_yyyymmdd(d["date"])
        us_settled_cases_ts = self.get_data_us_settled_cases_ts()
        us_settled_cases_ts[date_label] = settled_cases
        us_positive_rate_ts = self.get_data_us_positive_rate_ts()
        # Use cases as placeholder for now, will calc later
        us_positive_rate_ts[date_label] = positive_cases
        us_pending_cases_ts = self.get_data_us_pending_cases_ts()
        us_pending_cases_ts[date_label] = pending_cases
        return d["date"]

    def _parse_header_us_states(self, header_line):
        self.headers_us_states = self.partition_csv_line(header_line)

    def _handle_data_line_us_states(self, current_line):
        d = self._parse_data_line(current_line, self.headers_us_states)
        if not _is_valid_state_line(d, current_line):
            return
        state_fips = state_fips_map[d["state"]]
        (settled_cases, positive_cases, pending_cases) = _extract_testing_data(d)
        date_label = get_title_from_yyyymmdd(d["date"])
        state_settled_cases_ts = self.get_data_state_settled_cases_ts(state_fips)
        state_settled_cases_ts[date_label] = settled_cases
        state_positive_rate_ts = self.get_data_state_positive_rate_ts(state_fips)
        state_positive_rate_ts[date_label] = positive_cases
        state_pending_cases_ts = self.get_data_state_pending_cases_ts(state_fips)
        state_pending_cases_ts[date_label] = pending_cases
        us_settled_cases_dl = self.get_data_us_settled_cases_dl(date_label)
        us_settled_cases_dl[state_fips] = settled_cases
        us_positive_rate_dl = self.get_data_us_positive_rate_dl(date_label)
        us_positive_rate_dl[state_fips] = positive_cases
        us_pending_cases_dl = self.get_data_us_pending_cases_dl(date_label)
        us_pending_cases_dl[state_fips] = pending_cases
        return d["date"]

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

    def _date_handler_positive_rates(self, date_label):
        # Process us rates
        positive_rate_ts = self.get_data_us_positive_rate_ts()
        settled_cases = self.get_data_us_settled_cases_ts().get(date_label, 0)
        positive_cases = positive_rate_ts.get(date_label, 0)
        prev_settled_cases = 0
        prev_positive_cases = 0
        if date_label != self.least_recent_date:
            prev_settled_cases = self.get_data_us_settled_cases_ts().get(
                get_title_yesterday(date_label), 0
            )
            prev_positive_cases = self.get_data_us_positive_rate_ts().get(
                get_title_yesterday(date_label), 0
            )
        positive_rate_ts[date_label] = _get_positive_rate(
            settled_cases, positive_cases, prev_settled_cases, prev_positive_cases
        )
        # Process us states
        for state_fips in state_fips_map.values():
            positive_rate_ts = self.get_data_state_positive_rate_ts(state_fips)
            if len(positive_rate_ts) == 0:
                # No date for this fips
                continue
            settled_cases = self.get_data_state_settled_cases_ts(state_fips).get(
                date_label, 0
            )
            positive_cases = positive_rate_ts.get(date_label, 0)
            prev_settled_cases = 0
            prev_positive_cases = 0
            if date_label != self.least_recent_date:
                prev_settled_cases = self.get_data_state_settled_cases_ts(
                    state_fips
                ).get(get_title_yesterday(date_label), 0)
                prev_positive_cases = self.get_data_state_positive_rate_ts(
                    state_fips
                ).get(get_title_yesterday(date_label), 0)
            positive_rate = _get_positive_rate(
                settled_cases, positive_cases, prev_settled_cases, prev_positive_cases
            )
            positive_rate_ts[date_label] = positive_rate
            self.get_data_us_positive_rate_dl(date_label)[state_fips] = positive_rate

    def _calculate_positive_rates(self):
        # Calculate us positive_rates
        self.process_date_range(
            self.most_recent_date,
            self.least_recent_date,
            self._date_handler_positive_rates,
        )

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
    return (settled_cases, positive, pending_cases)


def _get_positive_rate(
    settled_cases, positive_cases, prev_settled_cases, prev_positive_cases
):
    new_settled_cases = settled_cases - prev_settled_cases
    return (
        math.floor(10000 * (positive_cases - prev_positive_cases) / new_settled_cases)
        if new_settled_cases > 0
        else 0
    ) / 100


def _is_valid_state_line(d, line):
    if not "date" in d:
        print(f"No date in line '{line}', skiping")
        return False
    if "state" not in d:
        print(f"No state info in line '{line}', skiping")
        return False
    if d["state"] not in state_fips_map:
        print(f"No such state in state_fips_map: {d['state']}")
        return False
    return True
