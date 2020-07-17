from .covid_parser import CovidParser


class Votes2016Parser(CovidParser):
    def __init__(self, data, data_source_folder):
        super().__init__(data, data_source_folder)
        self.source_file_counties = (
            f"{data_source_folder}/2016-election-county-results/counties.csv"
        )
        self.headers = []
        # In votes2016 data, v for all votes, t stands for trump,
        # c for clinton, j for johnson

    def _parse_data_line(self, data_line, headers):
        return dict(zip(headers, self.partition_csv_line(data_line),))

    def parse(self):
        # data['0']['votes2016']
        votes_us = self.get_data_votes2016_us()
        with open(self.source_file_counties) as fp:
            header_line = fp.readline()
            self.headers = self.partition_csv_line(header_line)
            current_line = fp.readline()
            while current_line:
                d = dict(zip(self.headers, self.partition_csv_line(current_line),))
                county_fips = d["cod"]
                state_fips = county_fips[:2]
                # data['0']['votes2016']['xx']
                votes_us_state = self.get_data_votes2016_us(state_fips)
                # data['xx']['votes2016']
                votes_state = self.get_data_votes2016_state(state_fips)
                # data['xx']['votes2016']['xxxxx']
                votes_county = self.get_data_votes2016_state(county_fips)
                votes = {
                    "v": int(d["votes"]),
                    d["candidate1"]: int(d[f"c{d[d['candidate1']]}v"]),
                    d["candidate2"]: int(d[f"c{d[d['candidate2']]}v"]),
                    d["candidate3"]: int(d[f"c{d[d['candidate3']]}v"]),
                }
                # Merge votes into votes_us, votes_us_state, votes_state, votes_county
                merge_votes(votes_us, votes)
                merge_votes(votes_us_state, votes)
                merge_votes(votes_state, votes)
                merge_votes(votes_county, votes)
                current_line = fp.readline()

    # fips must be None, '0', or a 2-digit state fips code
    def get_data_votes2016_us(self, fips=None):
        if fips is None or fips == "0":
            return self.get_data_us("votes2016")
        elif len(fips) == 2:
            return self.get_data_us("votes2016", fips)
        else:
            print(f"Wrong state fips {fips} encounted while parsing votes2016 file")

    def get_data_votes2016_state(self, fips):
        if len(fips) == 2:
            return self.get_data_state(fips, "votes2016")
        elif len(fips) == 5:
            return self.get_data_state(fips[:2], "votes2016", fips)
        else:
            print(f"Wrong fips {fips} encounted while parsing votes2016 file")


def merge_votes(votes_to, votes_from):
    for k in votes_from:
        if k not in votes_to:
            votes_to[k] = 0
        votes_to[k] = votes_to[k] + votes_from[k]

