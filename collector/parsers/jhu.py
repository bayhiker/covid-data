import csv
from datetime import date, timedelta
from ..utils import (
    get_date_from_title,
    get_title_from_date,
    get_date_titles,
    parse_int,
)
from ..us import (
    state_fips_iterator,
    split_county_fips,
    new_york_county_population,
)
from .special_counties import SpecialCounties


class JhuParser:
    def __init__(self, data, data_source_folder):
        jhu_data_folder = f"{data_source_folder}/COVID-19/csse_covid_19_data/csse_covid_19_time_series"
        self.raw_data_file_confirmed = (
            f"{jhu_data_folder}/time_series_covid19_confirmed_US.csv"
        )
        self.raw_data_file_deaths = (
            f"{jhu_data_folder}/time_series_covid19_deaths_US.csv"
        )
        self.headers_time_series_confirmed = []
        self.headers_time_series_deaths = []
        self.least_recent_date = "1/22/20"
        self.most_recent_date = ""  # In m/dd/yy, just like in JHU dataset
        self.date_keys_history = []
        # To be inited after loading headers->least/most_recent_date
        self.special_counties = None
        self.data = data

    def set_headers(self, headers_line_confirmed, headers_line_deaths):
        self.headers_time_series_confirmed = partition_csv_line(headers_line_confirmed)
        self.headers_time_series_deaths = partition_csv_line(headers_line_deaths)
        header_length_confirmed = len(self.headers_time_series_confirmed)
        self.most_recent_date = self.headers_time_series_confirmed[
            header_length_confirmed - 1
        ]
        self.date_keys_history = get_date_titles(
            self.least_recent_date, self.most_recent_date
        )
        end_date = get_date_from_title(self.most_recent_date)
        self.special_counties = SpecialCounties(
            get_date_from_title(self.least_recent_date),
            get_date_from_title(self.most_recent_date),
        )
        print(f"Most recent date is {self.most_recent_date}")

    def parse_line_confirmed(self, line):
        d = dict(zip(self.headers_time_series_confirmed, partition_csv_line(line),))
        format_county_data(d)
        return d

    def parse_line_deaths(self, line):
        d = dict(zip(self.headers_time_series_deaths, partition_csv_line(line),))
        format_county_data(d)
        return d

    def _get_default_data_root(self):
        return {
            "least_recent_date": self.least_recent_date,
            "most_recent_date": self.most_recent_date,
            "confirmed": {"time_series": {},},
            "deaths": {"time_series": {},},
            "mobility": {"time_series": {},},
            "population": {},
            "names": {},  # key is state or county fips, value is name
            "hashes": {},  # key is a hash of full name, value is fips, only used for counties in state data
        }

    def process_county_data(self, county_data):
        county_data_confirmed = county_data["confirmed"]
        county_data_deaths = county_data["deaths"]
        assert county_data_confirmed["FIPS"] == county_data_deaths["FIPS"]
        # For counties reported within a healthcare region, distribute regional to counties
        self.special_counties.update_county_data(county_data)
        fips = county_data_confirmed["FIPS"]
        (state_fips, county_fips) = split_county_fips(fips)
        data_us = self.data["US"].setdefault("0", self._get_default_data_root())
        data_state = self.data["US"].setdefault(
            state_fips, self._get_default_data_root()
        )
        county_population = int(county_data_deaths["Population"])
        county_name = county_data_deaths["Admin2"]
        county_name_hash = (
            _get_county_name_hash(county_name)
            if county_name is not None
            and len(county_name) > 2
            and not county_name.startswith("Out of ")
            else -1
        )
        state_name = county_data_deaths["Province_State"]
        # No roll up for county data, therefore no need for a separtae time_series
        data_county = data_state.setdefault(
            fips,
            {
                "least_recent_date": self.least_recent_date,
                "most_recent_date": self.most_recent_date,
                "confirmed": {
                    x: parse_int(county_data_confirmed[x])
                    for x in self.date_keys_history
                },
                "deaths": {
                    x: parse_int(county_data_deaths[x]) for x in self.date_keys_history
                },
                "population": county_population,
                "name": county_name,
                "hash": county_name_hash,
            },
        )
        data_us["population"].setdefault(state_fips, 0)
        data_us["population"][state_fips] += county_population
        if not state_fips in data_us["names"]:
            data_us["names"][state_fips] = state_name
        data_state["population"].setdefault(fips, 0)
        data_state["population"][fips] += county_population
        data_state["names"][fips] = county_name
        if county_name_hash > 0 and county_name_hash in data_state["hashes"]:
            current_county_name = data_state["names"][
                data_state["hashes"][county_name_hash]
            ]
            assert county_name == current_county_name or print(
                f'Hash Conflict: {county_name} and {data_state["names"][data_state["hashes"][county_name_hash]]}'
            )
        data_state["hashes"][county_name_hash] = fips

        def update_us_and_state(case_type, num_cases):
            def get_default_cases():
                return {
                    "minCases": 1000000,
                    "maxCases": -1,
                    "minPerCapita": 100000000,
                    "maxPerCapita": -1,
                }

            data_us[case_type]["time_series"].setdefault(d, 0)
            data_us[case_type]["time_series"][d] += num_cases
            data_us[case_type].setdefault(d, get_default_cases())
            data_us[case_type][d].setdefault(state_fips, 0)
            data_us[case_type][d][state_fips] += num_cases
            data_state[case_type].setdefault(d, get_default_cases())
            data_state[case_type][d][fips] = num_cases
            if county_fips not in ("800", "900", "888", "999"):
                # Only consider min/maxCases for regular counties
                if data_state[case_type][d]["minCases"] > num_cases:
                    data_state[case_type][d]["minCases"] = num_cases
                if data_state[case_type][d]["maxCases"] < num_cases:
                    data_state[case_type][d]["maxCases"] = num_cases
            data_state[case_type]["time_series"].setdefault(d, 0)
            data_state[case_type]["time_series"][d] += num_cases

        for d in self.date_keys_history:
            update_us_and_state(
                "confirmed", parse_int(county_data_confirmed.get(d, "0"))
            )
            update_us_and_state("deaths", parse_int(county_data_deaths.get(d, "0")))

    def process_jhu_data_files(self, county_data_processor):
        with open(self.raw_data_file_confirmed) as fp_confirmed, open(
            self.raw_data_file_deaths
        ) as fp_deaths:
            # Skip the first header line
            line_confirmed = fp_confirmed.readline()
            line_deaths = fp_deaths.readline()
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
                if parsed_line_confirmed["FIPS"].startswith("000"):
                    print(
                        f"Ignoring US territories for now. FIPS was {parsed_line_confirmed['FIPS']}"
                    )
                    continue
                county_data_processor(
                    {"confirmed": parsed_line_confirmed, "deaths": parsed_line_deaths}
                )

    def parse(self):
        # Set headers from
        with open(self.raw_data_file_confirmed) as fp_confirmed, open(
            self.raw_data_file_deaths
        ) as fp_deaths:
            line_confirmed = fp_confirmed.readline()
            line_deaths = fp_deaths.readline()
            self.set_headers(line_confirmed, line_deaths)
        # Proprocess JHU county time series data, fill self.special_counties
        self.process_jhu_data_files(self.special_counties.preprocess_county_data)
        # Read in and process JHU county time series data
        self.process_jhu_data_files(self.process_county_data)
        # Go through data_us["0"]['confirmed'][by_date], each date, set 'minCases' and 'maxCases'
        for d in self.date_keys_history:
            for case_type in ("confirmed", "deaths"):
                data_us_daily = self.data["US"]["0"][case_type][d]
                population = self.data["US"]["0"]["population"]
                for fips in state_fips_iterator():
                    if data_us_daily["maxCases"] < data_us_daily[fips]:
                        data_us_daily["maxCases"] = data_us_daily[fips]
                    if data_us_daily["minCases"] > data_us_daily[fips]:
                        data_us_daily["minCases"] = data_us_daily[fips]
                    casesPerCapita = int(
                        data_us_daily[fips] / population[fips] * pow(10, 6)
                    )
                    if data_us_daily["maxPerCapita"] < casesPerCapita:
                        data_us_daily["maxPerCapita"] = casesPerCapita
                    if data_us_daily["minPerCapita"] > casesPerCapita:
                        data_us_daily["minPerCapita"] = casesPerCapita
        for k in state_fips_iterator():
            if not (len(k) == 2 and k.isdigit()):
                continue
            data_state = self.data["US"][k]
            state_fips = k
            population = data_state["population"]
            for case_type in ("confirmed", "deaths"):
                for d in self.date_keys_history:
                    data_state_daily = data_state[case_type][d]
                    for county_fips in data_state_daily:
                        if not (len(county_fips) == 5 and county_fips.isdigit()):
                            continue
                        if (
                            county_fips in ("99999", "88888")
                            or county_fips.startswith("800")
                            or county_fips.startswith("900")
                        ):
                            continue
                        if (
                            int(county_fips) % 1000 < 600
                            and int(county_fips) % 1000 >= 555
                        ):
                            # Made up regions
                            continue
                        casesPerCapita = int(
                            data_state_daily[county_fips]
                            / population[county_fips]
                            * pow(10, 6)
                        )
                        if data_state_daily["maxPerCapita"] < casesPerCapita:
                            data_state_daily["maxPerCapita"] = casesPerCapita
                        if data_state_daily["minPerCapita"] > casesPerCapita:
                            data_state_daily["minPerCapita"] = casesPerCapita
        self.special_counties.verify_regional_data()


def partition_csv_line(line):
    return list(csv.reader([line]))[0]


def format_county_data(county_data_dict):
    fips = county_data_dict["FIPS"] if "FIPS" in county_data_dict else None
    combined_key = (
        county_data_dict["Combined_Key"] if "Combined_Key" in county_data_dict else None
    )
    if fips is not None and fips.endswith(".0"):
        fips = fips[0:-2]
    if fips is None or len(fips) == 0:
        if combined_key == "Dukes and Nantucket,Massachusetts,US":
            fips = "25555"  # Use Dukes county only for now, Nantucket is 25019
        elif combined_key == "Kansas City,Missouri,US":
            fips = "29555"  # Cass, Clay, Jackson, Platte, use Jackson for now
        elif combined_key == "Michigan Department of Corrections (MDOC), Michigan, US":
            fips = "26555"  # Made-up fips code for MDOC
        elif combined_key == "Federal Correctional Institution (FCI), Michigan, US":
            fips = "26556"  # Made-up fips code for FCI, Michigan
        # https://ibis.health.utah.gov/ibisph-view/about/LocalHealth.html
        elif combined_key == "Bear River, Utah, US":
            fips = "49555"  # Made-up fips for bear river city UTAH
        elif combined_key == "Central Utah, Utah, US":
            # Sanpete, Sevier, and Piute, as well as the eastern (east of longitude 113W)
            # halves of Juab, Millard, and Beaver counties
            fips = "49556"  # Use made-up fips for central utah
        elif combined_key == "Southeast Utah, Utah, US":
            fips = "49557"  # Use made-up fips 101 for central utah
        elif combined_key == "Southwest Utah, Utah, US":
            fips = "49558"  # Use made-up fips 101 for central utah
        elif combined_key == "Weber-Morgan, Utah, US":
            fips = "49559"  # Use made-up fips 101 for central utah
        elif combined_key == "TriCounty, Utah, US":
            fips = "49560"  # Use made-up fips 101 for central utah
        else:
            fips = ""
            print(
                f"No FIPS found, ignoring {combined_key} for now, county_data_dict was {county_data_dict}"
            )
    if fips in ["60", "66", "69", "72", "78"]:
        # Us territories, no counties, use xx001 like DC, and fill county name with territory name
        fips = f"{fips}001"
        county_data_dict["Admin2"] = county_data_dict["Province_State"]
    if fips == "36061":
        # Correct NY county population
        county_data_dict["Population"] = new_york_county_population
    county_data_dict["FIPS"] = fips.zfill(5)


def _get_county_name_hash(county_name):
    # A sevent digit integer,
    assert county_name is not None and len(county_name) > 2
    county_name_hash = 1
    for c in county_name.lower():
        county_name_hash = (county_name_hash * ord(c)) % 9999999
    return county_name_hash
