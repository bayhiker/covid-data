from collector.parsers import CovidTrackingParser


class CovidTrackingParserTestCase:
    def test_parser(self):
        data = {}
        covidTrackingParser = CovidTrackingParser(data, "../covid-data-sources")
        covidTrackingParser.parse()
        us_settled_cases_ts = covidTrackingParser.get_data_us_settled_cases_ts()
        us_positive_rate_ts = covidTrackingParser.get_data_us_positive_rate_ts()
        us_pending_cases_ts = covidTrackingParser.get_data_us_pending_cases_ts()
        assert len(us_settled_cases_ts) == len(us_positive_rate_ts)
        assert len(us_settled_cases_ts) == len(us_pending_cases_ts)
        assert len(us_settled_cases_ts) > 100
