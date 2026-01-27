"""
DateParser tool for deterministic date parsing and duration calculation.

Receives structured date input (year, month) from LLM extraction
and calculates durations deterministically.

Edge cases handled:
- Ongoing roles (is_ongoing=True) -> use reference date
- Missing end date (not ongoing) -> assume 1 month duration
- Missing start date -> flag anomaly, 0 duration
- Inverted dates (start > end) -> auto-swap with anomaly flag
- Future dates -> flag as anomaly
- Duration stated -> parse and compare with calculated
"""

import re
from datetime import date
from typing import Optional

from dateutil.relativedelta import relativedelta

from .models import (
    DateAnomaly,
    EnrichedExperience,
    RawDateInput,
    RawExperienceInput,
)


class DateParser:
    """
    Parses date inputs and calculates durations deterministically.
    """

    def __init__(self, reference_date: Optional[date] = None):
        """
        Initialize with a reference date for "ongoing" calculations.

        Args:
            reference_date: The date to use for ongoing roles. Defaults to today.
        """
        self.reference_date = reference_date or date.today()

    def process_experience(self, raw: RawExperienceInput) -> EnrichedExperience:
        """
        Process a raw experience entry and calculate duration.

        Args:
            raw: RawExperienceInput from LLM extraction

        Returns:
            EnrichedExperience with calculated duration and anomalies
        """
        # Parse dates
        start_date = self._date_from_input(raw.start_date)
        end_date = self._date_from_input(raw.end_date)

        start_estimated = raw.start_date.is_estimated if raw.start_date else False
        end_estimated = raw.end_date.is_estimated if raw.end_date else False

        anomaly = None
        duration_months = 0

        # Handle missing dates
        if start_date is None and end_date is None:
            anomaly = DateAnomaly.MISSING_BOTH
            duration_months = 1  # Assume minimum 1 month
        elif start_date is None:
            anomaly = DateAnomaly.MISSING_START
            duration_months = 1  # Assume minimum 1 month
        else:
            # Determine effective end date
            if raw.is_ongoing:
                # Ongoing role - use reference date
                effective_end = self.reference_date
                end_estimated = False  # Reference date is exact
            elif end_date is None:
                # End date not mentioned and not ongoing - assume 1 month
                effective_end = date(start_date.year, start_date.month, 1)
                duration_months = 1
            else:
                effective_end = end_date

            # Check for inverted dates
            if end_date and start_date > end_date:
                anomaly = DateAnomaly.INVERTED
                start_date, end_date = end_date, start_date
                effective_end = end_date

            # Check for future dates
            if anomaly is None:
                if start_date > self.reference_date:
                    anomaly = DateAnomaly.FUTURE_START
                elif effective_end > self.reference_date and not raw.is_ongoing:
                    anomaly = DateAnomaly.FUTURE_END

            # Calculate duration if not already set
            if duration_months == 0:
                duration_months = self._calculate_months(start_date, effective_end)

        # Parse stated duration and check for divergence
        duration_stated_months = None
        duration_divergence = None

        if raw.duration_stated:
            duration_stated_months = self._parse_duration_text(raw.duration_stated)
            if duration_stated_months and duration_months > 0:
                divergence = abs(duration_months - duration_stated_months) / duration_stated_months
                duration_divergence = round(divergence, 2)

                # Flag if significant divergence and no other anomaly
                if divergence > 0.2 and anomaly is None:
                    anomaly = DateAnomaly.DURATION_MISMATCH

        return EnrichedExperience(
            company=raw.company,
            title=raw.title,
            location=raw.location,
            experience_type=raw.experience_type,
            start_date=start_date,
            end_date=end_date if not raw.is_ongoing else None,
            is_ongoing=raw.is_ongoing,
            duration_months=duration_months,
            start_estimated=start_estimated,
            end_estimated=end_estimated,
            duration_stated=raw.duration_stated,
            duration_stated_months=duration_stated_months,
            duration_divergence=duration_divergence,
            anomaly=anomaly,
            key_contributions=raw.key_contributions,
            skills_demonstrated=raw.skills_demonstrated,
        )

    def process_experiences(
        self, entries: list[RawExperienceInput]
    ) -> list[EnrichedExperience]:
        """Process multiple experience entries."""
        return [self.process_experience(e) for e in entries]

    def _date_from_input(self, raw_date: Optional[RawDateInput]) -> Optional[date]:
        """Convert RawDateInput to date object."""
        if raw_date is None:
            return None

        try:
            # Use first of month
            return date(raw_date.year, raw_date.month, 1)
        except ValueError:
            return None

    def _calculate_months(self, start: date, end: date) -> int:
        """
        Calculate months between two dates.

        Returns minimum 1 month for valid date ranges.
        """
        if start > end:
            return 1

        delta = relativedelta(end, start)
        months = delta.years * 12 + delta.months

        # Add partial month if > 15 days
        if delta.days > 15:
            months += 1

        return max(1, months)

    def _parse_duration_text(self, text: str) -> Optional[int]:
        """
        Parse duration from text like "2.5 years" or "8 months".

        Returns duration in months, or None if unparseable.
        """
        if not text:
            return None

        text = text.lower().strip()

        # Try to match patterns like "2.5 years", "8 months", "1 year 6 months"
        years: float = 0
        months: float = 0

        # Pattern: X.X years
        year_match = re.search(r"(\d+\.?\d*)\s*(?:years?|yrs?)", text)
        if year_match:
            years = float(year_match.group(1))

        # Pattern: X months
        month_match = re.search(r"(\d+\.?\d*)\s*(?:months?|mos?)", text)
        if month_match:
            months = float(month_match.group(1))

        total = int(years * 12 + months)
        return total if total > 0 else None
