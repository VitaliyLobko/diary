"""Validated field types shared across the request schemas."""

from datetime import date
from typing import Annotated

from pydantic import AfterValidator

# Oldest plausible date of birth. Anything earlier is a typo or a probe, not a
# person a school keeps records on.
MIN_DOB = date(1900, 1, 1)


def _check_dob(value: date) -> date:
    if value < MIN_DOB:
        raise ValueError(f"dob must not be earlier than {MIN_DOB.isoformat()}")
    if value > date.today():
        raise ValueError("dob must not be in the future")
    return value


Dob = Annotated[date, AfterValidator(_check_dob)]
