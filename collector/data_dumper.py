import os
import json
from .us import split_county_fips


class DataDumper:
    def __init__(self, data, target_folder):
        self.json_folder = target_folder
        self.data = data

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
