"""Download NYC TLC parquet files into the bronze landing volume.

For each month from START to the latest published one, upload the file if it isn't
in the landing zone yet. The TLC CloudFront never returns 404 (a missing file and a
rate limit both answer 403 with no Retry-After), so we discover the latest published
month first and then fail loudly on any non-200 within that range (it can only be
throttling, never missing data). Requests back off exponentially on 403/429/5xx.

Functions are ordered by the call sequence (callers before the helpers they call); main, the
entry point, sits at the bottom.
"""

import time
from datetime import date
from io import BytesIO

import requests
from config import get_logger, landing_dir
from databricks.sdk import WorkspaceClient

logger = get_logger(__name__)

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
START = (2023, 1)
TAXI_TYPES = ("yellow", "green")
MAX_RETRIES = 10
MAX_BACKOFF_SECONDS = 90
LOOKBACK_MONTHS = 6
PACING_SECONDS = 1.0

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "nyc-tlc-pipeline"})


def download_taxi(w: WorkspaceClient, taxi: str) -> None:
    """Land every published, not-yet-landed file for one taxi."""
    end = latest_published(taxi)
    logger.info("%s: latest published month is %04d-%02d", taxi, *end)
    volume_dir = landing_dir(taxi)
    landed = existing_files(w, volume_dir)
    for ym in months_range(end):
        filename = filename_for(taxi, ym)
        if filename in landed:
            logger.info("skip (already landed): %s", filename)
            continue
        download_month(w, taxi, ym, volume_dir)
        time.sleep(PACING_SECONDS)


def latest_published(taxi: str) -> tuple[int, int]:
    """Most recent published month, walking back from today (403 = not published yet, no retry)."""
    ym = (date.today().year, date.today().month)
    for _ in range(LOOKBACK_MONTHS):
        url = url_for(taxi, ym)
        response = SESSION.head(url, timeout=60)
        if response.status_code == 200:
            return ym
        ym = prev_month(ym)
    raise RuntimeError(f"no published {taxi} file found in the last {LOOKBACK_MONTHS} months")


def existing_files(w: WorkspaceClient, volume_dir: str) -> set[str]:
    """Names already in the landing dir (empty on first run, before the dir exists)."""
    try:
        return {entry.name for entry in w.files.list_directory_contents(volume_dir)}
    except Exception:
        return set()


def months_range(end: tuple[int, int]) -> list[tuple[int, int]]:
    """Every (year, month) from START up to and including end."""
    months = []
    ym = START
    while ym <= end:
        months.append(ym)
        ym = next_month(ym)
    return months


def download_month(w: WorkspaceClient, taxi: str, ym: tuple[int, int], volume_dir: str) -> None:
    """Download one month's file into the landing volume (fail loudly on non-200)."""
    filename = filename_for(taxi, ym)
    url = url_for(taxi, ym)
    response = request(url)
    if response.status_code != 200:
        raise RuntimeError(
            f"failed to download {filename}: HTTP {response.status_code} within the "
            f"published range (rate limited or blocked, not missing data)"
        )
    w.files.upload(f"{volume_dir}/{filename}", BytesIO(response.content), overwrite=False)
    logger.info("downloaded: %s (%d bytes)", filename, len(response.content))


def request(url: str) -> requests.Response:
    """HTTP request with exponential backoff on throttling (403/429/5xx; no Retry-After is sent)."""
    delay = 2.0
    for attempt in range(MAX_RETRIES):
        response = SESSION.request("GET", url, timeout=300)
        throttled = response.status_code in (403, 429) or response.status_code >= 500
        if not throttled or attempt == MAX_RETRIES - 1:
            return response
        logger.warning(
            "throttled (HTTP %d) on %s, retrying in %.0fs", response.status_code, url, delay
        )
        time.sleep(delay)
        delay = min(delay * 2, MAX_BACKOFF_SECONDS)
    return response


def url_for(taxi: str, ym: tuple[int, int]) -> str:
    """CloudFront URL for a taxi type and month."""
    return f"{BASE_URL}/{filename_for(taxi, ym)}"


def filename_for(taxi: str, ym: tuple[int, int]) -> str:
    """Parquet file name for a taxi type and month."""
    return f"{taxi}_tripdata_{ym[0]:04d}-{ym[1]:02d}.parquet"


def next_month(ym: tuple[int, int]) -> tuple[int, int]:
    """The (year, month) after ym."""
    year, month = ym
    return (year + 1, 1) if month == 12 else (year, month + 1)


def prev_month(ym: tuple[int, int]) -> tuple[int, int]:
    """The (year, month) before ym."""
    year, month = ym
    return (year - 1, 12) if month == 1 else (year, month - 1)


def main() -> None:
    """Download every published, not-yet-landed TLC file into the landing volume."""
    w = WorkspaceClient()
    for taxi in TAXI_TYPES:
        download_taxi(w, taxi)


if __name__ == "__main__":
    main()
