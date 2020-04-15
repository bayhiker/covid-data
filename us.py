import json

# To be consistent, population is sum of all population in ./json/state.json
united_states = {"population": 315482390}

state_fips_map = {
    "AK": "02",
    "AL": "01",
    "AR": "05",
    "AS": "60",
    "AZ": "04",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DC": "11",
    "DE": "10",
    "FL": "12",
    "GA": "13",
    "GU": "66",
    "HI": "15",
    "IA": "19",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "MA": "25",
    "MD": "24",
    "ME": "23",
    "MI": "26",
    "MN": "27",
    "MO": "29",
    "MS": "28",
    "MT": "30",
    "NC": "37",
    "ND": "38",
    "NE": "31",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NV": "32",
    "NY": "36",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "PR": "72",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VA": "51",
    "VI": "78",
    "VT": "50",
    "WA": "53",
    "WI": "55",
    "WV": "54",
    "WY": "56",
}


def _load_fips_state_map():
    with open("./json/states.json") as f:
        return json.load(f)


# State only, no territories
def state_fips_iterator():
    n = 0
    while n < 56:
        n += 1
        if n in (3, 7, 14, 43, 52):
            n += 1
        yield str(n).zfill(2)


def is_state_fips(fips):
    return fips is not None and len(fips) == 2 and fips.isdigit()


def is_county_fips(fips):
    return fips is not None and len(fips) == 5 and fips.isdigit()


def split_county_fips(county_fips):
    return (
        None
        if (county_fips is None or len(county_fips) != 5)
        else (county_fips[:2], county_fips[2:])
    )


fips_state_map = _load_fips_state_map()

if __name__ == "__main__":
    population = 0
    for state_fips in fips_state_map:
        if "population" in fips_state_map[state_fips]:
            population += fips_state_map[state_fips]["population"]
    print(population)
