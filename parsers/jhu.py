import os
import csv
import json
from datetime import date, timedelta
from sklearn.linear_model import LogisticRegression
from utils import (
    get_date_from_title,
    get_title_from_date,
    get_date_titles,
    get_title_future_or_past,
    get_title_tomorrow,
    parse_int,
)
from us import (
    state_fips_iterator,
    split_county_fips,
    new_york_county_population,
)
from descarte import DescartesMobilityParser
from special_counties import SpecialCounties


class TimeSeriesParser:
    def __init__(self):
        self.raw_data_file_confirmed = "../../covid-data-sources/COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"
        self.raw_data_file_deaths = "../../covid-data-sources/COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv"
        # self.json_folder = "../covid/data"
        self.json_folder = "../data/covid"
        self.headers_time_series_confirmed = []
        self.headers_time_series_deaths = []
        self.least_recent_date = "1/22/20"
        self.most_recent_date = ""  # In m/dd/yy, just like in JHU dataset
        self.date_keys_history = []
        self.date_keys_prediction = []
        self.days_to_predict = 14
        # To be inited after loading headers->least/most_recent_date
        self.descartes = None
        self.special_counties = None
        # us level: self.data["US"]['0'][confirmed/deaths/mobility/data_title]
        # state level: self.data["US"]['06'][confirmed/deaths/mobility/data_title]
        # county level: self.data["US"]['06']['06085'][confirmed/deaths/mobility]
        self.data = {"US": {}}

    @staticmethod
    def format_county_data(county_data_dict):
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
                fips = "25555"  # Use Dukes county only for now, Nantucket is 25019
            elif combined_key == "Kansas City,Missouri,US":
                fips = "29555"  # Cass, Clay, Jackson, Platte, use Jackson for now
            elif (
                combined_key
                == "Michigan Department of Corrections (MDOC), Michigan, US"
            ):
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
        self.date_keys_history = get_date_titles(
            self.least_recent_date, self.most_recent_date
        )
        end_date = get_date_from_title(self.most_recent_date)
        self.date_keys_prediction = get_date_titles(
            get_title_tomorrow(self.most_recent_date),
            get_title_future_or_past(self.most_recent_date, self.days_to_predict),
        )
        self.descartes = DescartesMobilityParser(
            self.least_recent_date, self.most_recent_date, self.days_to_predict
        )
        self.special_counties = SpecialCounties(
            get_date_from_title(self.least_recent_date),
            get_date_from_title(self.most_recent_date),
        )
        print(f"Most recent date is {self.most_recent_date}")

    def parse_line_confirmed(self, line):
        d = dict(
            zip(
                self.headers_time_series_confirmed,
                TimeSeriesParser.partition_csv_line(line),
            )
        )
        TimeSeriesParser.format_county_data(d)
        return d

    def parse_line_deaths(self, line):
        d = dict(
            zip(
                self.headers_time_series_deaths,
                TimeSeriesParser.partition_csv_line(line),
            )
        )
        TimeSeriesParser.format_county_data(d)
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

    @staticmethod
    def _get_county_name_hash(county_name):
        # A sevent digit integer,
        assert county_name is not None and len(county_name) > 2
        county_name_hash = 1
        for c in county_name.lower():
            county_name_hash = (county_name_hash * ord(c)) % 9999999
        return county_name_hash

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
            TimeSeriesParser._get_county_name_hash(county_name)
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

    def _get_json_path(self, fips):
        assert len(fips) in (1, 2, 5)
        path = None
        if len(fips) <= 2:
            # US county data fips '0', or 2-digit state data
            path = f"{self.json_folder}/us/{fips}.json"
        else:
            # With assert, len must be 5
            (state_fips, county_fips) = split_county_fips(fips)
            path = f"{self.json_folder}/us/{state_fips}/{county_fips}.json"
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
        for state_fips in self.data["US"]:
            data_state = self.data["US"][state_fips]
            for k in list(data_state.keys()):
                if len(k) == 5 and k.isdigit():
                    # This is a county json data
                    self._write_json_data(k, data_state.pop(k))
            self._write_json_data(state_fips, data_state)

    """
        state_populations = self.data["US"]["0"]["population"]
        for state_fips in state_populations:
            print(f"population {state_fips}: {state_populations[state_fips]}")
            county_populations = self.data["US"][state_fips]["population"]
            for county_fips in county_populations:
                print(
                    f"    population {county_fips}: {county_populations[county_fips]}"
                )
                """

    def predict(self):
        # Anaylyze timeseries data for us, states, and counties
        # with scikit logistic regression
        data_us = self.data["US"]["0"]
        for case_type in ["confirmed", "deaths"]:
            # Predicted cases for US
            cases_time_series_us = data_us[case_type]["time_series"]
            predictions_us = self.predict_with_time_series(
                cases_time_series_us, data_us["mobility"]["time_series"],
            )
            data_us[case_type]["time_series"] = {
                **cases_time_series_us,
                **predictions_us,
            }
            for state_fips in state_fips_iterator():
                print(f"Predicting state {state_fips}")
                data_state = self.data["US"][state_fips]
                cases_time_series_state = data_state[case_type]["time_series"]
                # Predicted cases for state with this state_fips
                predictions_state = self.predict_with_time_series(
                    cases_time_series_state, data_state["mobility"]["time_series"],
                )
                # Update data_state predictions
                data_state[case_type]["time_series"] = {
                    **cases_time_series_state,
                    **predictions_state,
                }
                for prediction_title_state in predictions_state:
                    # Update corresponding data_us[case_type][date][state_fips]
                    if not prediction_title_state in data_us[case_type]:
                        data_us[case_type][prediction_title_state] = {}
                    data_us[case_type][prediction_title_state][
                        state_fips
                    ] = predictions_state[prediction_title_state]
                # Predict for each county in state_fips
                for county_fips in list(data_state.keys()):
                    if len(county_fips) != 5 or not county_fips.isdigit():
                        continue
                    data_county = data_state[county_fips]
                    case_time_series_county = {
                        x: data_county[case_type][x] for x in self.date_keys_history
                    }
                    mobility_county = data_county["mobility"]
                    predicted_cases_county = self.predict_with_time_series(
                        case_time_series_county, mobility_county
                    )
                    # Update county record
                    data_county[case_type] = {
                        **case_time_series_county,
                        **predicted_cases_county,
                    }
                    for predicted_title_county in predicted_cases_county:
                        # Update data_state[case_type][date][state_fips]
                        if predicted_title_county not in data_state[case_type]:
                            data_state[case_type][predicted_title_county] = {}
                        data_state[case_type][predicted_title_county][
                            county_fips
                        ] = predicted_cases_county[predicted_title_county]

    def predict_with_time_series(self, case_time_series, mobility_series):
        logit = LogisticRegression(solver="lbfgs", max_iter=1000)
        x = [
            [d, mobility_series[self.date_keys_history[d]]]
            for d in range(len(self.date_keys_history))
        ]
        y = [case_time_series[d] for d in self.date_keys_history]
        y_set = set(y)
        if len(y_set) == 1:
            # Only a single value in all historic cases, should be 0
            only_value = y_set.pop()
            return dict(
                zip(self.date_keys_prediction, [only_value] * self.days_to_predict)
            )
        x_future = [
            [len(x) + i, mobility_series[self.date_keys_prediction[i]]]
            for i in range(self.days_to_predict)
        ]
        logit.fit(x, y)
        predicted_cases = logit.predict(x_future)
        # Convert NumPy int to python int
        # Avoid Object of type 'int64' is not JSON serializable
        predicted_cases = [int(x) for x in predicted_cases]
        # Apparently, predicted cases should not drop
        if predicted_cases[0] < y[len(y) - 1]:
            predicted_cases[0] = y[len(y) - 1]
        for i in range(len(predicted_cases) - 1):
            if predicted_cases[i] > predicted_cases[i + 1]:
                predicted_cases[i + 1] = predicted_cases[i]

        return dict(zip(self.date_keys_prediction, predicted_cases))

    def add_mobility_data(self):
        # Update us mobility-time_series
        data_us = self.data["US"]["0"]
        data_us["mobility"]["time_series"] = self.descartes.get_us_m50_index()
        for state_fips in state_fips_iterator():
            # Update state mobility-timeseries
            mobility_state = self.descartes.get_m50_index(state_fips)
            data_state = self.data["US"][state_fips]
            data_state["mobility"]["time_series"] = mobility_state
            # Update us[mobility][date_title][state_fips]
            for date_title in mobility_state:
                mobility_data_daily = data_us["mobility"].setdefault(date_title, {})
                mobility_data_daily[state_fips] = mobility_state[date_title]
            # data_state['names'] should have been set, call confirmed/deaths parsing before mobility parsing
            for county_fips in data_state["names"]:
                if len(county_fips) != 5 or not county_fips.isdigit():
                    continue
                mobility_county = self.descartes.get_m50_index(county_fips)
                data_state[county_fips]["mobility"] = mobility_county
                for date_title in mobility_county:
                    mobility_data_daily = data_state["mobility"].setdefault(
                        date_title, {}
                    )
                    mobility_data_daily[county_fips] = mobility_county[date_title]

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
        self.add_mobility_data()
        self.special_counties.verify_regional_data()
        # self.predict()
        self.dump_data()
