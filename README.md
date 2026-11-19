# StackWatch

StackWatch is a local workspace for engineering teams to follow public open source projects they depend on. Create a watchlist, compare completed weekly commit activity against a recent baseline, and keep review notes for your next team discussion.

![StackWatch data workflow](docs/architecture.svg)

StackWatch is an independent project and is not affiliated with GitHub or the projects in the example catalog.

## What the product does

- Create separate workspaces and select projects from a reviewed catalog.
- See weekly commit counts and compare the latest completed week with the average of the preceding four weeks.
- Identify changes to review and save local notes for a team discussion.
- Download a workspace report as CSV.
- See whether each project's latest data fetch succeeded, is pending or failed.

Counts are aggregate signals, not measures of quality, security, maintenance commitment or suitability. Repositories have different workflows and should not be ranked against each other by commit count.

## Run locally

Python 3.10 or newer is required. The local dashboard and collection use the standard library and SQLite.

```bash
python -m stackwatch.cli sync
python -m stackwatch.app
```

Open <http://127.0.0.1:8092>, create a workspace, select projects and save the selection. The local database is created under the ignored `data/` directory. A new checkout starts empty until a sync succeeds. The server is intended for local use and binds to localhost only.

GitHub may initially return 202 while preparing statistics. Such projects are marked `pending`, not interpreted as zero. If the API limits requests, the collector stops subsequent requests and preserves existing observations. Try again after the appropriate rate-limit reset.

## How the comparison works

The dashboard ignores the current incomplete week. For each repository it compares the most recent completed week with the average of the four preceding contiguous completed weeks. A change is only shown when all five weeks exist, the baseline is nonzero and the newest week is no more than 14 days old. A 50% increase or decrease is highlighted; otherwise the series is labelled steady. These are descriptive rules, not predictions or alerts about software health.

The data comes from [GitHub's weekly commit activity endpoint](https://docs.github.com/en/rest/metrics/statistics#get-the-last-year-of-commit-activity), which reports aggregate counts for the past year. GitHub statistics exclude merge commits and may be delayed or unavailable. Data fetched at different times can cover different windows. The dashboard uses its observation table directly; the dbt models are separate analytical views.

## Data workflows

The current scope is weekly aggregate commit activity from the reviewed catalog in [catalog.json](catalog.json). Collection validates weekly counts and upserts them by repository and week. A quality workflow checks available history. A reporting workflow prepares workspace summaries. Dagster coordinates the three assets and provides four jobs: collection, quality, reporting and the full daily workflow.

```bash
python -m pip install -r requirements.txt
dagster dev -m stackwatch.orchestration
```

Enable the daily schedule in the Dagster UI when desired. Individual downstream jobs require upstream materializations. Partial source failures are recorded without erasing prior data. This is not yet a GH Archive ingestion system and it does not track releases, issues or pull requests.

## PostgreSQL and dbt

Set a local password, then start the PostgreSQL container and build the views. This example uses a simple alphanumeric password. URL-encode special characters used in a connection URL.

```bash
export POSTGRES_PASSWORD='choose-a-local-password'
export PGPASSWORD="$POSTGRES_PASSWORD"
export PGPORT=5434
export DATABASE_URL="postgresql://stackwatch:${POSTGRES_PASSWORD}@127.0.0.1:5434/stackwatch"
docker compose up -d
python -m stackwatch.cli sync
dbt build --project-dir dbt --profiles-dir dbt
python -m stackwatch.app
```

On PowerShell use `$env:POSTGRES_PASSWORD`, `$env:PGPASSWORD`, `$env:PGPORT` and `$env:DATABASE_URL` instead of `export`. The dbt project provides staging, latest-observation and rolling-observation views. A rolling observation window is not necessarily a contiguous calendar window if data is missing.

## AWS export

`infra/` defines a private, versioned, encrypted S3 bucket. Review the configuration and cost before deployment. With an existing bucket and AWS credentials configured outside the repository:

```bash
python -m stackwatch.cli archive-s3 --bucket YOUR_BUCKET --key stackwatch/weekly.csv
```

Only repository names, week timestamps and aggregate counts are exported. Terraform deployment and live S3 writes have not been verified. The S3 code is tested with a stub; no cloud service is created automatically.

## Privacy and scope

The collector deliberately requests GitHub's aggregate weekly activity endpoint for a fixed catalog of organization-owned repositories. It does not ingest GH Archive, individual contributors, PR bodies or issue contents. Responses are processed in memory and only selected aggregate fields are persisted. A repository name itself may identify an individual, so adding arbitrary repositories is intentionally unsupported. Workspace names and review notes are user input stored locally. Do not put personal or confidential information in them.

These precautions do not by themselves establish eligibility under a third party's rules. Review the actual data and intended use with the program before submission.

## Tests and roadmap

```bash
python -m unittest discover -s tests -v
```

See [roadmap](ROADMAP.md) for planned work. Licensed under [MIT](LICENSE).
