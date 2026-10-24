from datetime import datetime, timezone

import pytest

from bikemap.timefmt import format_utc, parse_utc


def test_parse_basic():
    assert parse_utc("2026-05-03T07:42:10Z") == datetime(2026, 5, 3, 7, 42, 10, tzinfo=timezone.utc)


def test_parse_fraction():
    assert parse_utc("2026-05-03T07:42:10.500Z").microsecond == 500000


@pytest.mark.parametrize("value", ["2026-05-03T07:42:10", "2026-05-03T09:42:10+02:00",
                                   "2026-05-03", "2026-05-32T00:00:00Z", None, ""])
def test_parse_rejects(value):
    with pytest.raises(ValueError):
        parse_utc(value)


def test_format():
    assert format_utc(datetime(2026, 5, 3, 7, 42, 10, 900, tzinfo=timezone.utc)) == "2026-05-03T07:42:10Z"
    with pytest.raises(ValueError):
        format_utc(datetime(2026, 5, 3))
