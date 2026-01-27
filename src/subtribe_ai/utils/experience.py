"""
ExperienceCalculator tool for aggregating experience and detecting patterns.

Takes enriched experience entries (after DateParser) and calculates:
- Total experience by type
- Overlap detection and adjustment
- Gap detection
- Anomaly aggregation
"""

from datetime import date
from typing import Optional

from .models import (
    DateAnomaly,
    EmploymentGap,
    EnrichedExperience,
    ExperienceSummary,
    ExperienceType,
)


class ExperienceCalculator:
    """
    Calculates aggregated experience metrics from enriched entries.
    """

    def __init__(
        self,
        significant_gap_months: int = 6,
        reference_date: Optional[date] = None,
    ):
        """
        Args:
            significant_gap_months: Threshold for significant gaps (default 6)
            reference_date: Reference date for calculations (default today)
        """
        self.significant_gap_months = significant_gap_months
        self.reference_date = reference_date or date.today()

    def calculate_summary(
        self, entries: list[EnrichedExperience]
    ) -> ExperienceSummary:
        """
        Calculate complete experience summary.

        Args:
            entries: List of EnrichedExperience from DateParser

        Returns:
            ExperienceSummary with aggregated metrics
        """
        if not entries:
            return ExperienceSummary(
                total_months=0,
                total_years=0.0,
                entries=[],
            )

        # Calculate by type
        type_months = self._calculate_by_type(entries)

        # Detect overlaps
        overlap_months, has_overlaps = self._detect_overlaps(entries)

        # Detect gaps (employment types only)
        employment_entries = [
            e
            for e in entries
            if e.experience_type
            in [
                ExperienceType.FULL_TIME,
                ExperienceType.INTERNSHIP,
                ExperienceType.CONTRACT,
                ExperienceType.FREELANCE,
            ]
        ]
        gaps = self._detect_gaps(employment_entries)

        # Collect anomaly descriptions
        anomalies = self._collect_anomalies(entries)

        # Calculate totals
        raw_total = sum(type_months.values())
        total_months = max(0, raw_total - overlap_months)
        total_years = round(total_months / 12, 1)

        return ExperienceSummary(
            total_months=total_months,
            total_years=total_years,
            full_time_months=type_months.get(ExperienceType.FULL_TIME, 0),
            internship_months=type_months.get(ExperienceType.INTERNSHIP, 0),
            freelance_months=type_months.get(ExperienceType.FREELANCE, 0),
            contract_months=type_months.get(ExperienceType.CONTRACT, 0),
            part_time_months=type_months.get(ExperienceType.PART_TIME, 0),
            startup_months=type_months.get(ExperienceType.STARTUP_FOUNDER, 0),
            project_months=(
                type_months.get(ExperienceType.ACADEMIC_PROJECT, 0)
                + type_months.get(ExperienceType.PERSONAL_PROJECT, 0)
            ),
            has_overlaps=has_overlaps,
            overlap_months=overlap_months,
            gaps=gaps,
            has_significant_gaps=any(g.is_significant for g in gaps),
            anomalies=anomalies,
            entries=entries,
        )

    def _calculate_by_type(
        self, entries: list[EnrichedExperience]
    ) -> dict[ExperienceType, int]:
        """Sum duration by experience type."""
        type_months: dict[ExperienceType, int] = {}

        for entry in entries:
            exp_type = entry.experience_type
            if exp_type not in type_months:
                type_months[exp_type] = 0
            type_months[exp_type] += entry.duration_months

        return type_months

    def _detect_overlaps(
        self, entries: list[EnrichedExperience]
    ) -> tuple[int, bool]:
        """
        Detect overlapping employment periods.

        Returns:
            (overlap_months, has_overlaps)
        """
        valid_entries = [
            e for e in entries if e.start_date and e.duration_months > 0
        ]

        if len(valid_entries) < 2:
            return 0, False

        # Sort by start_date - all entries have start_date after filter above
        sorted_entries = sorted(
            valid_entries,
            key=lambda e: e.start_date or date.min,
        )

        total_overlap = 0
        has_overlaps = False

        for i in range(len(sorted_entries) - 1):
            current = sorted_entries[i]
            current_end = current.end_date or self.reference_date

            for j in range(i + 1, len(sorted_entries)):
                next_entry = sorted_entries[j]
                next_start = next_entry.start_date
                if next_start is None:
                    continue

                if next_start < current_end:
                    has_overlaps = True
                    next_end = next_entry.end_date or self.reference_date

                    overlap_start = next_start
                    overlap_end = min(current_end, next_end)

                    if overlap_end > overlap_start:
                        overlap_months = (
                            (overlap_end.year - overlap_start.year) * 12
                            + overlap_end.month
                            - overlap_start.month
                        )
                        total_overlap += max(0, overlap_months)

        return total_overlap, has_overlaps

    def _detect_gaps(
        self, entries: list[EnrichedExperience]
    ) -> list[EmploymentGap]:
        """
        Detect gaps between employment periods.
        """
        valid_entries = [
            e for e in entries if e.start_date and e.duration_months > 0
        ]

        if len(valid_entries) < 2:
            return []

        # Sort by end date
        sorted_entries = sorted(
            valid_entries,
            key=lambda e: e.end_date or self.reference_date,
        )

        gaps: list[EmploymentGap] = []

        for i in range(len(sorted_entries) - 1):
            current = sorted_entries[i]
            next_entry = sorted_entries[i + 1]

            current_end = current.end_date or self.reference_date
            next_start = next_entry.start_date
            if next_start is None:
                continue

            if next_start > current_end:
                gap_months = (
                    (next_start.year - current_end.year) * 12
                    + next_start.month
                    - current_end.month
                )

                if gap_months > 1:  # Ignore 1-month gaps
                    gaps.append(
                        EmploymentGap(
                            after_company=current.company,
                            before_company=next_entry.company,
                            gap_start=current_end,
                            gap_end=next_start,
                            gap_months=gap_months,
                            is_significant=gap_months >= self.significant_gap_months,
                        )
                    )

        return gaps

    def _collect_anomalies(self, entries: list[EnrichedExperience]) -> list[str]:
        """Collect human-readable anomaly descriptions."""
        anomalies = []

        for entry in entries:
            if entry.anomaly:
                if entry.anomaly == DateAnomaly.INVERTED:
                    anomalies.append(
                        f"{entry.company}: Dates were inverted, auto-corrected"
                    )
                elif entry.anomaly == DateAnomaly.FUTURE_START:
                    anomalies.append(
                        f"{entry.company}: Start date is in the future"
                    )
                elif entry.anomaly == DateAnomaly.FUTURE_END:
                    anomalies.append(
                        f"{entry.company}: End date is in the future"
                    )
                elif entry.anomaly == DateAnomaly.MISSING_START:
                    anomalies.append(
                        f"{entry.company}: Missing start date, assumed 1 month"
                    )
                elif entry.anomaly == DateAnomaly.MISSING_BOTH:
                    anomalies.append(
                        f"{entry.company}: Missing dates, assumed 1 month"
                    )
                elif entry.anomaly == DateAnomaly.DURATION_MISMATCH:
                    anomalies.append(
                        f"{entry.company}: Calculated {entry.duration_months}mo "
                        f"differs from stated '{entry.duration_stated}' "
                        f"({entry.duration_divergence:.0%} divergence)"
                    )

        return anomalies
