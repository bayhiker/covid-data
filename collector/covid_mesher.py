#!/usr/bin/env python

from .parsers import JhuParser
from .parsers import DescartesMobilityParser
from .parsers import CovidTrackingParser
from .parsers import Votes2016Parser
from .data_dumper import DataDumper

# from covid_predictor import CovidPredictor


class CovidMesher:
    def __init__(self, data_source_folder, data_target_folder):
        self.days_to_predict = 14
        self.data_source_folder = data_source_folder
        self.data_target_folder = data_target_folder
        # us level: self.data["US"]['0'][confirmed/deaths/mobility/data_title]
        # state level: self.data["US"]['06'][confirmed/deaths/mobility/data_title]
        # county level: self.data["US"]['06']['06085'][confirmed/deaths/mobility]
        self.data = {"US": {}}

    def mesh(self):
        jhuParser = JhuParser(self.data, self.data_source_folder)
        jhuParser.parse()
        descartes = DescartesMobilityParser(
            self.data,
            self.data_source_folder,
            jhuParser.least_recent_date,
            jhuParser.most_recent_date,
            self.days_to_predict,
        )
        descartes.parse()
        # covidPredictor = CovidPredictor(
        #    self.days_to_predict,
        #    jhuParser.least_recent_date,
        #    jhuParser.most_recent_date,
        #    self.data,
        # )
        # covidPredictor.predict()
        covidTrackingParser = CovidTrackingParser(self.data, self.data_source_folder)
        covidTrackingParser.parse()
        votes2016Parser = Votes2016Parser(self.data, self.data_source_folder)
        votes2016Parser.parse()

        dataDumper = DataDumper(self.data, self.data_target_folder)
        dataDumper.dump_data()
