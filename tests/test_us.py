from collector.us import is_state_fips, is_county_fips, split_county_fips


class UtilsTestCase:
    def test_is_state_fips(self):
        assert not is_state_fips("")
        assert not is_state_fips("222")
        assert not is_state_fips("a2")
        assert not is_state_fips("0")
        assert is_state_fips("12")
