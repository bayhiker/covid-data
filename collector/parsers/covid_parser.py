import abc
import csv
from collector.utils import get_date_from_title, get_title_from_date, date_range


class CovidParser(abc.ABC):
    def __init__(self, data, data_source_folder):
        self.data = data
        self.data_source_folder = data_source_folder

    @abc.abstractmethod
    def parse(self):
        pass

    def partition_csv_line(self, line):
        return list(csv.reader([line]))[0]

    def process_date_range(self, start_date_title, end_date_title, date_handler):
        for d in date_range(
            get_date_from_title(start_date_title), get_date_from_title(end_date_title)
        ):
            date_handler(get_title_from_date(d))

    def get_data(self, *field_names):
        d = self.data
        for field_name in field_names:
            d = d.setdefault(field_name, {})
        return d

    def get_data_state(self, fips, *args):
        return self.get_data("US", fips, *args)

    def get_data_us(self, *args):
        return self.get_data_state("0", *args)

    def get_data_us_time_series(self, data_type):
        return self.get_data_state_time_series("0", data_type)

    def get_data_us_date_label(self, data_type, date_label):
        return self.get_data_state("0", *data_type, date_label)

    def get_data_state_time_series(self, fips, data_type):
        return self.get_data_state(fips, *data_type, "time_series")

    def get_data_state_date_label(self, fips, data_type, date_label):
        return self.get_data_state(fips, *data_type, date_label)

    def get_data_global_time_series(self, data_type):
        return self.get_data_state_time_series("g", data_type)

    def get_data_global_date_label(self, data_type, date_label):
        return self.get_data_state("g", *data_type, date_label)
