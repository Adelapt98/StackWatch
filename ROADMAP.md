# Roadmap

StackWatch is an early product focused on a useful review workflow for engineering teams. The following are planned enhancements.

## Product

- Add project detail views with calendar-aligned charts and clear source freshness.
- Add configurable review rules and comparisons for a team's own objectives.
- Support pinned review items, ownership-free tags and richer report exports.
- Add accessibility improvements and validate the workflow with real users.

## Data and reliability

- Improve backoff, retry scheduling, observability and handling of GitHub's 202 and rate-limit responses.
- Add source freshness history, per-project data coverage and automatic correction handling.
- Review the data rights and personal-data implications of any expanded catalog or source before enabling it.
- Investigate aggregate-only sources for releases and project activity without ingesting contributor information.
- Consider GH Archive only after explicit eligibility clarification and a documented data-protection design. Raw event data contains user information.

## Data platform

- Add dbt data tests for uniqueness, time gaps and metric constraints.
- Build separate observable jobs for approved new sources, backfills and historical summaries.
- Evaluate Parquet and PySpark on measured workloads rather than adding infrastructure without a need.
- Exercise S3 export with an isolated AWS account, restricted permissions, lifecycle policies and cost controls.
- Add integration CI for PostgreSQL, dbt and Dagster and document operations and recovery.

## Delivery

- Expand documentation, reproducible packaging and deployment guidance.
- Add user feedback, release notes, migration procedures and backup/retention options.

These are intended directions, not features currently implemented or a promise of dates.
