"""Download NYC TLC parquet files into the bronze landing volume.

For each month in the range, upload the file if it isn't in the landing zone yet. The range is
[START, END] (`YYYY-MM`, resolved in config from the job params or env): START defaults to 2023-01
(where the dataset begins), and when END is unset the range ends at the latest published month. A
month is handled as a running index (year*12 + month), so building the range and stepping back are
plain integer arithmetic. The TLC CloudFront never returns 404 (a missing file and a rate limit both
answer 403 with no Retry-After), so we discover the latest published month and then fail loudly on
any non-200 within the range (it can only be throttling, never missing data). Requests back off
exponentially on 403/429/5xx.

Functions are ordered by the call sequence (callers before the helpers they call); main, the
entry point, sits at the bottom.
"""

import time
from datetime import date
from io import BytesIO

import requests
from config import END, START, get_logger, landing_dir
from databricks.sdk import WorkspaceClient

logger = get_logger(__name__)

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
TAXI_TYPES = ("yellow", "green")
MAX_RETRIES = 10
MAX_BACKOFF_SECONDS = 90
LOOKBACK_MONTHS = 6
PACING_SECONDS = 1.0

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "nyc-tlc-pipeline"})


def download_taxi(w: WorkspaceClient, taxi: str) -> None:
    """Land every published, not-yet-landed file for one taxi over the configured range."""
    end = END or latest_published(taxi)
    logger.info("%s: range %s to %s", taxi, START, end)
    volume_dir = landing_dir(taxi)
    landed = existing_files(w, volume_dir)
    for ym in months_range(START, end):
        filename = filename_for(taxi, ym)
        if filename in landed:
            logger.info("skip (already landed): %s", filename)
            continue
        download_month(w, taxi, ym, volume_dir)
        time.sleep(PACING_SECONDS)


def latest_published(taxi: str) -> str:
    """Most recent published month (YYYY-MM), walking back from today (403 = not published yet)."""
    index = to_index(date.today().strftime("%Y-%m"))
    for _ in range(LOOKBACK_MONTHS):
        ym = to_month(index)
        if SESSION.head(url_for(taxi, ym), timeout=60).status_code == 200:
            return ym
        index -= 1
    raise RuntimeError(f"no published {taxi} file found in the last {LOOKBACK_MONTHS} months")


def existing_files(w: WorkspaceClient, volume_dir: str) -> set[str]:
    """Names already in the landing dir (empty on first run, before the dir exists)."""
    try:
        return {entry.name for entry in w.files.list_directory_contents(volume_dir)}
    except Exception:
        return set()


def months_range(start: str, end: str) -> list[str]:
    """Every month (YYYY-MM) in [start, end], inclusive."""
    return [to_month(i) for i in range(to_index(start), to_index(end) + 1)]


def download_month(w: WorkspaceClient, taxi: str, ym: str, volume_dir: str) -> None:
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


def url_for(taxi: str, ym: str) -> str:
    """CloudFront URL for a taxi type and month."""
    return f"{BASE_URL}/{filename_for(taxi, ym)}"


def filename_for(taxi: str, ym: str) -> str:
    """Parquet file name for a taxi type and month (YYYY-MM)."""
    return f"{taxi}_tripdata_{ym}.parquet"


def to_index(ym: str) -> int:
    """YYYY-MM -> a running month number, so range and stepping are integer arithmetic."""
    year, month = map(int, ym.split("-"))
    return year * 12 + month - 1


def to_month(index: int) -> str:
    """Inverse of to_index: a running month number -> YYYY-MM."""
    year, month = divmod(index, 12)
    return f"{year}-{month + 1:02d}"


def main() -> None:
    """Download every published, not-yet-landed TLC file in the range into the landing volume."""
    w = WorkspaceClient()
    for taxi in TAXI_TYPES:
        download_taxi(w, taxi)


if __name__ == "__main__":
    main()
