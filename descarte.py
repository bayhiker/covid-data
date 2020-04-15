from datetime import date
import ndjson
from utils import (
    get_title_from_date,
    get_date_from_title,
    get_date_titles,
    get_title_future_or_past,
)
from us import (
    state_fips_iterator,
    fips_state_map,
    united_states,
    is_state_fips,
    is_county_fips,
    split_county_fips,
)


class DescartesMobilityParser:
    def __init__(self, start_date_title, end_date_title, days_to_predict):
        self.ndjson_path = "../covid-data-sources/DL-COVID-19/DL-us-mobility.ndjson"
        self.m50 = {}  # fips->{date->m50} absolute mobility level defined by Descartes
        self.m50_index = {}  # fips-> {date->m50_index}, 100*m50/m50_norm
        self.start_date_title = start_date_title
        self.end_date_title = end_date_title
        self.days_to_predict = days_to_predict
        self.load()

    def load(self):
        with open(self.ndjson_path) as f:
            reader = ndjson.reader(f)
            for record in reader:
                fips = record["fips"]
                date_list = [format_date_title(x) for x in record["date"]]
                m50_list = record["m50"]
                m50_index_list = record["m50_index"]
                self.m50[fips] = dict(zip(date_list, m50_list))
                self.m50_index[fips] = dict(zip(date_list, m50_index_list))
        # Generate US average m50 and m50_index
        self.m50["0"] = _get_us_weighted_average(self.m50)
        self.m50_index["0"] = _get_us_weighted_average(self.m50_index)

    def get_m50(self, fips):
        return self._get_local_mobility_data(self.m50, fips)

    def get_m50_index(self, fips):
        return self._get_local_mobility_data(self.m50_index, fips)

    def _get_local_mobility_data(self, mobility_data_dict, fips):
        raw_mobility_data = None
        if fips in mobility_data_dict:
            return self.patch_daily_mobility(mobility_data_dict[fips])
        # We know we have mobility data for all states
        if is_county_fips(fips):
            return self.patch_daily_mobility(
                mobility_data_dict[split_county_fips(fips)[0]]
            )
        print(f"Invalid fips {fips} when retrieving mobility data")

    def get_us_m50(self):
        return self.patch_daily_mobility(self.m50["0"])

    def get_us_m50_index(self):
        mobility_data = self.patch_daily_mobility(self.m50_index["0"])
        counter = 0
        for k in mobility_data:
            counter += 1
        return mobility_data

    #
    # Make sure daily_mobility dictionary  (date_title-> m50 or m50_index)
    # has all values between start_ to end_date_title. Missing values are
    # filled with last seen value. Values missing at the front are filled
    # with the first value
    #
    def patch_daily_mobility(self, mobility_data):
        if mobility_data is None:
            return None
        last_valid_value = None
        # Find the first mobility data
        first_title_with_mobility = None
        for date_title in get_date_titles(self.start_date_title, self.end_date_title):
            if date_title in mobility_data:
                last_valid_value = mobility_data[date_title]
                first_title_with_mobility = date_title
                break
        for date_title in get_date_titles(self.start_date_title, self.end_date_title):
            if date_title in mobility_data:
                last_valid_value = mobility_data[date_title]
            else:
                mobility_data[date_title] = last_valid_value
        # Patch mobility for days_to_predict with latest_valid_value
        for date_title in get_date_titles(
            self.end_date_title,
            get_title_future_or_past(self.end_date_title, self.days_to_predict),
        ):
            mobility_data[date_title] = last_valid_value
        sorted_mobility_data = {
            k: mobility_data[k] for k in sorted(mobility_data.keys())
        }
        return {
            k: mobility_data[k]
            for k in sorted(
                mobility_data.keys(), key=lambda title: get_date_from_title(title)
            )
        }


def format_date_title(descartes_date):
    return get_title_from_date(_get_date_from_descarte_title(descartes_date))


def _get_date_from_descarte_title(title):
    assert title is not None
    (yyyy, mm, dd) = title.split("-")
    assert yyyy is not None and mm is not None and dd is not None
    return date(int(yyyy), int(mm.lstrip("0")), int(dd.lstrip("0")))


def _get_us_weighted_average(fips_data_map):
    us_weighted_values = {}  # date_title -> sum of weighted values
    us_total_weight = {}  # data_title -> subm of weights
    us_population = united_states["population"]
    for fips_state in state_fips_iterator():
        weight = fips_state_map[fips_state]["population"] / us_population
        state_data = fips_data_map[fips_state]
        for date_title in state_data:
            total_weighted_values = us_weighted_values.setdefault(date_title, 0)
            us_weighted_values[date_title] = (
                total_weighted_values + state_data[date_title] * weight
            )
            total_weight = us_total_weight.setdefault(date_title, 0)
            us_total_weight[date_title] = total_weight + weight
    return {
        k: round(us_weighted_values[k] / us_total_weight[k]) for k in us_weighted_values
    }
