import os
import csv
import json
from datetime import date, timedelta


class TimeSeriesParser:
    def __init__(self):
        self.raw_data_file_confirmed = "../covid-data-sources/COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"
        self.raw_data_file_deaths = "../covid-data-sources/COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv"
        # self.json_folder = "../covid/data"
        self.json_folder = "./data/covid"
        self.headers_time_series_confirmed = []
        self.headers_time_series_deaths = []
        self.least_recent_date = "1/22/20"
        self.most_recent_date = ""  # In m/dd/yy, just like in JHU dataset
        self.data = {"US": {}}

    @staticmethod
    def format_fips(county_data_dict):
        fips = county_data_dict["FIPS"] if "FIPS" in county_data_dict else None
        combined_key = (
            county_data_dict["Combined_Key"]
            if "Combined_Key" in county_data_dict
            else None
        )
        if fips is not None and fips.endswith(".0"):
            fips = fips[0:-2]
        if fips is None or len(fips) == 0:
            if combined_key == "Dukes and Nantucket,Massachusetts,US":
                fips = "25007"  # Use Dukes county only for now, Nantucket is 25019
            elif combined_key == "Kansas City,Missouri,US":
                fips = "28059"  # Cass, Clay, Jackson, Platte, use Jackson for now
            else:
                fips = ""
                print(f"Ignoring {combined_key} for now")
        county_data_dict["FIPS"] = fips.zfill(5)

    @staticmethod
    def split_fips(fips):
        # split fips into two digit state code and three digit county code
        assert len(fips) == 5
        return (fips[:2], fips[2:])

    @staticmethod
    def partition_csv_line(line):
        return list(csv.reader([line]))[0]

    def set_headers(self, headers_line_confirmed, headers_line_deaths):
        self.headers_time_series_confirmed = TimeSeriesParser.partition_csv_line(
            headers_line_confirmed
        )
        self.headers_time_series_deaths = TimeSeriesParser.partition_csv_line(
            headers_line_deaths
        )
        header_length_confirmed = len(self.headers_time_series_confirmed)
        self.most_recent_date = self.headers_time_series_confirmed[
            header_length_confirmed - 1
        ]
        print(f"Most recent date is {self.most_recent_date}")

    def get_date_keys(self):
        assert self.most_recent_date is not None
        (start_m, start_d, start_yy) = self.least_recent_date.split("/")
        (end_m, end_d, end_yy) = self.most_recent_date.split("/")
        start_date = date(int(f"20{start_yy}"), int(start_m), int(start_d))
        end_date = date(int(f"20{end_yy}"), int(end_m), int(end_d))
        return [
            (start_date + timedelta(x)).strftime("%-m/%-d/%y")
            for x in range(int((end_date - start_date).days + 1))
        ]

    def state_fips(self):
        n = 0
        while n < 56:
            n += 1
            if n in (3, 7, 14, 43, 52):
                n += 1
            yield str(n).zfill(2)

    def parse_line_confirmed(self, line):
        d = dict(
            zip(
                self.headers_time_series_confirmed,
                TimeSeriesParser.partition_csv_line(line),
            )
        )
        TimeSeriesParser.format_fips(d)
        return d

    def parse_line_deaths(self, line):
        d = dict(
            zip(
                self.headers_time_series_deaths,
                TimeSeriesParser.partition_csv_line(line),
            )
        )
        TimeSeriesParser.format_fips(d)
        return d

    def _get_default_data_root(self):
        return {
            "least_recent_date": self.least_recent_date,
            "most_recent_date": self.most_recent_date,
            "confirmed": {"time_series": {},},
            "deaths": {"time_series": {},},
            "population": {},
            "names": {},
        }

    def process_county_data(self, county_data_confirmed, county_data_deaths):
        assert county_data_confirmed["FIPS"] == county_data_deaths["FIPS"]
        fips = county_data_confirmed["FIPS"]
        (fips_state, fips_county) = TimeSeriesParser.split_fips(fips)
        data_us = self.data["US"].setdefault("0", self._get_default_data_root())
        data_state = self.data["US"].setdefault(
            fips_state, self._get_default_data_root()
        )
        county_population = int(county_data_deaths["Population"])
        county_name = county_data_deaths["Admin2"]
        state_name = county_data_deaths["Province_State"]
        # No roll up for county data, therefore no need for a separtae time_series
        data_county = data_state.setdefault(
            fips,
            {
                "least_recent_date": self.least_recent_date,
                "most_recent_date": self.most_recent_date,
                "confirmed": county_data_confirmed,
                "deaths": county_data_deaths,
                "population": county_population,
                "name": county_name,
            },
        )
        data_us["population"].setdefault(fips_state, 0)
        data_us["population"][fips_state] += county_population
        if not fips_state in data_us["names"]:
            data_us["names"][fips_state] = state_name
        data_state["population"].setdefault(fips, 0)
        data_state["population"][fips] += county_population
        data_state["names"][fips] = county_name

        def update_us_and_state(case_type, num_cases):
            data_us[case_type]["time_series"].setdefault(d, 0)
            data_us[case_type]["time_series"][d] += num_cases
            data_us[case_type].setdefault(
                d,
                {
                    "minCases": 1000000,
                    "maxCases": -1,
                    "minPerCapita": 100000000,
                    "maxPerCapita": -1,
                },
            )
            data_us[case_type][d].setdefault(fips_state, 0)
            data_us[case_type][d][fips_state] += num_cases
            data_state[case_type].setdefault(
                d,
                {
                    "minCases": 1000000,
                    "maxCases": -1,
                    "minPerCapita": 100000000,
                    "maxPerCapita": -1,
                },
            )
            data_state[case_type][d][fips] = num_cases
            if data_state[case_type][d]["minCases"] > num_cases:
                data_state[case_type][d]["minCases"] = num_cases
            if data_state[case_type][d]["maxCases"] < num_cases:
                data_state[case_type][d]["maxCases"] = num_cases
            data_state[case_type]["time_series"].setdefault(d, 0)
            data_state[case_type]["time_series"][d] += num_cases

        for d in self.get_date_keys():
            update_us_and_state("confirmed", int(county_data_confirmed.get(d, "0")))
            update_us_and_state("deaths", int(county_data_deaths.get(d, "0")))

    def _get_json_path(self, fips):
        assert len(fips) in (1, 2, 5)
        path = None
        if len(fips) <= 2:
            # US county data fips '0', or 2-digit state data
            path = f"{self.json_folder}/us/{fips}.json"
        else:
            # With assert, len must be 5
            (fips_state, fips_county) = TimeSeriesParser.split_fips(fips)
            path = f"{self.json_folder}/us/{fips_state}/{fips_county}.json"
        if path is not None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def _write_json_data(self, fips, data_for_fips):
        p = self._get_json_path(fips)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data_for_fips, f, ensure_ascii=False, indent=4)

    def dump_data(self):
        data_us = self.data["US"].pop("0", None)
        self._write_json_data("0", data_us)
        for fips_state in self.data["US"]:
            data_state = self.data["US"][fips_state]
            for k in list(data_state.keys()):
                if len(k) == 5 and k.isdigit():
                    # This is a county json data
                    self._write_json_data(k, data_state.pop(k))
            self._write_json_data(fips_state, data_state)

    """
        state_populations = self.data["US"]["0"]["population"]
        for fips_state in state_populations:
            print(f"population {fips_state}: {state_populations[fips_state]}")
            county_populations = self.data["US"][fips_state]["population"]
            for fips_county in county_populations:
                print(
                    f"    population {fips_county}: {county_populations[fips_county]}"
                )
                """

    def parse(self):
        # Read in JHU county time series data
        with open(self.raw_data_file_confirmed) as fp_confirmed, open(
            self.raw_data_file_deaths
        ) as fp_deaths:
            line_confirmed = fp_confirmed.readline()
            line_deaths = fp_deaths.readline()
            self.set_headers(line_confirmed, line_deaths)
            while line_confirmed and line_deaths:
                line_confirmed = fp_confirmed.readline()
                line_deaths = fp_deaths.readline()
                parsed_line_confirmed = self.parse_line_confirmed(line_confirmed)
                parsed_line_deaths = self.parse_line_deaths(line_deaths)
                if parsed_line_confirmed["FIPS"] != parsed_line_deaths["FIPS"]:
                    print("Mismatching confirmed and deaths lines")
                    print(f"C line:{line_confirmed}")
                    print(f"D line:{line_deaths}")
                    continue
                if parsed_line_confirmed["FIPS"] == "00000":
                    continue
                self.process_county_data(parsed_line_confirmed, parsed_line_deaths)
        # Go through data_us["0"]['confirmed'][by_date], each date, set 'minCases' and 'maxCases'
        for d in self.get_date_keys():
            for case_type in ("confirmed", "deaths"):
                data_us_daily = self.data["US"]["0"][case_type][d]
                population = self.data["US"]["0"]["population"]
                for fips in self.state_fips():
                    if data_us_daily["maxCases"] < data_us_daily[fips]:
                        data_us_daily["maxCases"] = data_us_daily[fips]
                    if data_us_daily["minCases"] > data_us_daily[fips]:
                        data_us_daily["minCases"] = data_us_daily[fips]
                    casesPerCapita = int(
                        data_us_daily[fips] / population[fips] * 1000000000
                    )
                    if data_us_daily["maxPerCapita"] < casesPerCapita:
                        data_us_daily["maxPerCapita"] = casesPerCapita
                    if data_us_daily["minPerCapita"] > casesPerCapita:
                        data_us_daily["minPerCapita"] = casesPerCapita
        for k in self.state_fips():
            if not (len(k) == 2 and k.isdigit()):
                continue
            data_state = self.data["US"][k]
            fips_state = k
            population = data_state["population"]
            for case_type in ("confirmed", "deaths"):
                for d in self.get_date_keys():
                    data_state_daily = data_state[case_type][d]
                    for fips_county in data_state_daily:
                        if not (len(fips_county) == 5 and fips_county.isdigit()):
                            continue
                        casesPerCapita = int(
                            data_state_daily[fips_county]
                            / population[fips_county]
                            * 1000000000
                        )
                        if data_state_daily["maxPerCapita"] < casesPerCapita:
                            data_state_daily["maxPerCapita"] = casesPerCapita
                        if data_state_daily["minPerCapita"] > casesPerCapita:
                            data_state_daily["minPerCapita"] = casesPerCapita

        self.dump_data()
