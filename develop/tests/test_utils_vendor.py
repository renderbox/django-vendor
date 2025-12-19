import datetime as dt

import pytest
from django.utils.translation import gettext_lazy

from vendor.utils import (
    force_str_if_proxy,
    get_future_date_days,
    get_future_date_months,
)


def test_get_future_date_months_handles_month_rollover_and_leap_year():
    start = dt.datetime(2024, 1, 31, tzinfo=dt.timezone.utc)

    result = get_future_date_months(start, 1)

    assert result == dt.datetime(2024, 2, 29, tzinfo=dt.timezone.utc)


def test_get_future_date_days_adds_days():
    start = dt.datetime(2024, 5, 1, tzinfo=dt.timezone.utc)
    assert get_future_date_days(start, 10) == dt.datetime(
        2024, 5, 11, tzinfo=dt.timezone.utc
    )


def test_force_str_if_proxy_converts_promise():
    lazy_str = gettext_lazy("hello")

    result = force_str_if_proxy(lazy_str)

    assert isinstance(result, str)
    assert result == "hello"
