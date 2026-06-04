"""Download NYC TLC parquet files into the bronze landing volume.

For each month from START to the latest published one, upload the file if it isn't
in the landing zone yet. The TLC CloudFront never returns 404 — a missing file and a
rate limit both answer 403 with no Retry-After — so we discover the latest published
month first and then fail loudly on any non-200 within that range (it can only be
throttling, never missing data). Requests back off exponentially on 403/429/5xx.
"""

import time
from datetime import date
from io import BytesIO

import requests
from config import CATALOG, get_logger
from databricks.sdk import WorkspaceClient

logger = get_logger(__name__)

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
START = (2023, 1)
TAXI_TYPES = ("yellow", "green")
MAX_RETRIES = 8
MAX_BACKOFF_SECONDS = 60
LOOKBACK_MONTHS = 6
PACING_SECONDS = 1.0

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "nyc-tlc-pipeline"})


def url_for(taxi: str, year: int, month: int) -> str:
    """CloudFront URL for a taxi type and month."""
    return f"{BASE_URL}/{taxi}_tripdata_{year:04d}-{month:02d}.parquet"


def request(method: str, url: str) -> requests.Response:
    """HTTP request with exponential backoff on throttling (403/429/5xx; no Retry-After is sent)."""
    delay = 2.0
    for attempt in range(MAX_RETRIES):
        response = SESSION.request(method, url, timeout=300)
        throttled = response.status_code in (403, 429) or response.status_code >= 500
        if not throttled or attempt == MAX_RETRIES - 1:
            return response
        logger.warning(
            "throttled (HTTP %d) on %s, retrying in %.0fs", response.status_code, url, delay
        )
        time.sleep(delay)
        delay = min(delay * 2, MAX_BACKOFF_SECONDS)
    return response


def latest_published(taxi: str) -> tuple[int, int]:
    """Most recent published month, walking back from today (403 = not published yet, no retry)."""
    year, month = date.today().year, date.today().month
    for _ in range(LOOKBACK_MONTHS):
        if SESSION.head(url_for(taxi, year, month), timeout=60).status_code == 200:
            return (year, month)
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    raise RuntimeError(f"no published {taxi} file found in the last {LOOKBACK_MONTHS} months")


def months_range(end: tuple[int, int]) -> list[tuple[int, int]]:
    """Every (year, month) from START up to and including end."""
    months = []
    year, month = START
    while (year, month) <= end:
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def existing_files(w: WorkspaceClient, volume_dir: str) -> set[str]:
    """Names already in the landing dir (empty on first run, before the dir exists)."""
    try:
        return {entry.name for entry in w.files.list_directory_contents(volume_dir)}
    except Exception:
        return set()


def main() -> None:
    """Download every published, not-yet-landed TLC file into the landing volume."""
    w = WorkspaceClient()
    ends = {taxi: latest_published(taxi) for taxi in TAXI_TYPES}
    for taxi, end in ends.items():
        logger.info("%s: latest published month is %04d-%02d", taxi, end[0], end[1])
        volume_dir = f"/Volumes/{CATALOG}/bronze/landing/{taxi}"
        landed = existing_files(w, volume_dir)
        for year, month in months_range(end):
            filename = f"{taxi}_tripdata_{year:04d}-{month:02d}.parquet"
            if filename in landed:
                logger.info("skip (already landed): %s", filename)
                continue
            response = request("GET", url_for(taxi, year, month))
            if response.status_code != 200:
                raise RuntimeError(
                    f"failed to download {filename}: HTTP {response.status_code} within the "
                    f"published range (rate limited or blocked, not missing data)"
                )
            w.files.upload(f"{volume_dir}/{filename}", BytesIO(response.content), overwrite=False)
            logger.info("downloaded: %s (%d bytes)", filename, len(response.content))
            time.sleep(PACING_SECONDS)


if __name__ == "__main__":
    main()
