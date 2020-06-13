from sklearn.linear_model import LogisticRegression
from .utils import (
    get_date_titles,
    get_title_future_or_past,
    get_title_tomorrow,
)
from .us import state_fips_iterator


class CovidPredictor:
    def __init__(self, data, days_to_predict, least_recent_data, most_recent_date):
        self.days_to_predict = days_to_predict
        self.least_recent_date = least_recent_data
        self.most_recent_date = most_recent_date
        self.date_keys_history = get_date_titles(
            self.least_recent_date, self.most_recent_date
        )
        self.date_keys_prediction = []
        self.date_keys_prediction = get_date_titles(
            get_title_tomorrow(self.most_recent_date),
            get_title_future_or_past(self.most_recent_date, self.days_to_predict),
        )
        self.data = data

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
