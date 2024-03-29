from datetime import date, timedelta, datetime


def get_title_from_date(d):
    return d.strftime("%-m/%-d/%y")


def get_date_from_title(title):
    assert title is not None
    return datetime.strptime(title, "%m/%d/%y").date()


def get_date_from_yyyymmdd(yyyymmdd):
    assert yyyymmdd is not None
    return datetime.strptime(yyyymmdd, "%Y%m%d").date()


def get_title_from_yyyymmdd(yyyymmdd):
    assert yyyymmdd is not None
    return get_title_from_date(get_date_from_yyyymmdd(yyyymmdd))


def get_date_titles(start_date_title, end_date_title):
    start_date = get_date_from_title(start_date_title)
    end_date = get_date_from_title(end_date_title)
    return [
        get_title_from_date(start_date + timedelta(x))
        for x in range(int((end_date - start_date).days + 1))
    ]


def get_date_titles_with_future(start_date_title, end_date_title, days_to_predict):
    return get_date_titles(
        start_date_title,
        get_title_from_date(get_date_from_title(end_date_title) + days_to_predict),
    )


def get_title_future_or_past(current_date_title, diff_days):
    d = get_date_from_title(current_date_title)
    return get_title_from_date(d + timedelta(diff_days))


def get_title_yesterday(current_date_title):
    return get_title_future_or_past(current_date_title, -1)


def get_title_tomorrow(current_date_title):
    return get_title_future_or_past(current_date_title, 1)


def date_range(start_date, end_date):
    days_apart = int((end_date - start_date).days)
    multiplier = 1 if days_apart > 0 else -1
    for n in range(abs(days_apart) + 1):
        yield start_date + timedelta(n * multiplier)


def parse_int(int_from_csv):
    # sometimes value is 0.0
    return int(float(int_from_csv))
