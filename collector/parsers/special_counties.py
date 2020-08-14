# TODO Use regional_data to somehow show bayarea cases, NYC cases, greater LA cases etc.
from datetime import timedelta
import math
from copy import deepcopy
from itertools import groupby
from ..utils import date_range, get_title_from_date, parse_int
from ..us import new_york_county_population


class SpecialCounties:
    def __init__(self, start_date, end_date):
        self.populations = {}
        # key is region fips, value is {"confirmed":{}, "deaths": {}}
        self.regional_data = {}
        self.start_date = start_date
        self.end_date = end_date
        self.region_fips = {
            "25007": "25555",
            "25019": "25555",
            "29037": "29555",
            "29047": "29555",
            "29095": "29555",
            "29165": "29555",
            "36005": "36555",
            "36047": "36555",
            "36061": "36555",
            "36081": "36555",
            "36085": "36555",
            "49003": "49555",
            "49005": "49555",
            "49033": "49555",
            "49001": "49558",
            "49017": "49558",
            "49021": "49558",
            "49025": "49558",
            "49053": "49558",
            "49007": "49557",
            "49015": "49557",
            "49019": "49557",
            "49009": "49560",
            "49013": "49560",
            "49047": "49560",
            "49023": "49556",
            "49027": "49556",
            "49031": "49556",
            "49039": "49556",
            "49041": "49556",
            "49055": "49556",
            "49029": "49559",
            "49057": "49559",
        }
        self.child_fips = {
            k: [j for j, _ in list(v)]
            for k, v in groupby(self.region_fips.items(), lambda x: x[1])
        }

    def preprocess_county_data(self, county_data):
        fips = get_fips_from_county_data(county_data)
        if fips == "36061":
            # NY county, at the same time is for NY region, change fips to 36555
            # and store it
            ny_regional_data = deepcopy(county_data)
            ny_region_fips = "36555"
            ny_regional_data["FIPS"] = ny_region_fips
            if ny_region_fips in self.populations:
                ny_regional_data["Population"] = self.populations[ny_region_fips]
            self.regional_data[ny_region_fips] = ny_regional_data
        if fips in self.child_fips:
            # This is an aggregated regional data line,
            self.regional_data[fips] = county_data
            # If regional data comes after member counties, then self.populations[fips]
            # would contain its regional pop. If regional data comes before all member counties
            # then self.populations[fips] is not set. Otherwise, self.population[fips]
            # would contain partial regional population, and the remaining populations
            # would be added in later
            self.regional_data[fips]["Population"] = (
                self.populations[fips] if fips in self.populations else 0
            )
            return
        if fips not in self.region_fips:
            # Not a county with regional fips, nothing to do
            return
        region_fips = self.region_fips[fips]
        county_fips = fips
        county_population = parse_int(county_data["deaths"]["Population"])
        if county_fips == "36061":
            # Make sure NY county population has been corrected.
            # JHU dataset has wrong population os 5M
            assert county_population == new_york_county_population
        self.populations[county_fips] = county_population
        region_population = self.populations.setdefault(region_fips, 0)
        self.populations[region_fips] = region_population + county_population
        if region_fips in self.regional_data:
            # In case regional data comes earlier than member county data,
            # Update Population field
            self.regional_data[region_fips]["Population"] = self.populations[
                region_fips
            ]

    def update_county_data(self, county_data):
        county_fips = get_fips_from_county_data(county_data)
        if county_fips not in self.region_fips:
            # Not a county a any region, nothing to do
            return
        region_fips = self.region_fips[county_fips]
        if not region_fips in self.regional_data:
            print(
                f"Regional county data not found: county_fips is {county_fips}, region_fips is {region_fips}"
            )
            return
        assert county_fips in self.populations and region_fips in self.populations
        regional_population = self.populations[region_fips]
        county_population = self.populations[county_fips]

        for case_type in ["confirmed", "deaths"]:
            key_counties_remaining = _get_key_counties_remaining(case_type)
            key_cases_remaining = _get_key_cases_remaining(case_type)
            regional_data = self.regional_data[region_fips]
            counties_remaining = regional_data.setdefault(
                key_counties_remaining, len(self.child_fips[region_fips])
            )
            regional_data[key_counties_remaining] = counties_remaining - 1
            for d in date_range(self.start_date, self.end_date + timedelta(1)):
                date_title = get_title_from_date(d)
                if date_title in regional_data[case_type]:
                    regional_cases = parse_int(regional_data[case_type][date_title])
                    county_cases = (
                        parse_int(county_data[case_type][date_title])
                        if date_title in county_data
                        else 0
                    )
                    if regional_cases > 0:
                        regional_data.setdefault(key_cases_remaining, {})
                        cases_remaining = parse_int(
                            regional_data[key_cases_remaining].setdefault(
                                date_title, regional_cases
                            )
                        )
                        weighted = math.floor(
                            regional_cases * county_population / regional_population
                        )
                        cases_remaining -= weighted
                        if counties_remaining == 1:
                            # Last county in this region, give all remaining cases caused by rounding error to the last county
                            weighted += cases_remaining
                            cases_remaining = 0
                        county_data[case_type][
                            date_title
                        ] = f"{county_cases + weighted}"
                        regional_data[key_cases_remaining][date_title] = cases_remaining

    def verify_regional_data(self):
        for case_type in ["confirmed", "deaths"]:
            key_counties_remaining = _get_key_counties_remaining(case_type)
            key_cases_remaining = _get_key_cases_remaining(case_type)
            for fips in self.regional_data:
                parent_data = self.regional_data[fips]
                assert (
                    parent_data[key_counties_remaining] == 0
                ), f"{key_counties_remaining} for FIPS {fips} was {parent_data[key_counties_remaining]}"
                if key_cases_remaining not in parent_data:
                    print(
                        f"No {case_type} cases in fips {fips} {parent_data[case_type]['Combined_Key']}"
                    )
                else:
                    for d in date_range(self.start_date, self.end_date):
                        date_title = get_title_from_date(d)
                        if date_title in parent_data[key_cases_remaining]:
                            parent_data[key_cases_remaining][date_title] == 0


def get_fips_from_county_data(county_data):
    assert county_data is not None
    assert "confirmed" in county_data and "deaths" in county_data
    assert county_data["confirmed"]["FIPS"] == county_data["deaths"]["FIPS"]
    return county_data["confirmed"]["FIPS"]


def _get_key_counties_remaining(case_type):
    return f"{case_type}-counties-remaining"


def _get_key_cases_remaining(case_type):
    return f"{case_type}-cases-remaining"
