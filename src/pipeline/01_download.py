"""Download NYC TLC parquet files into the bronze landing volume.

Incremental: walks every month from START to today for yellow and green, and
uploads only the files that aren't in the landing zone yet. Months the TLC hasn't
published return 403/404 and are skipped, so reruns just pick up new months.
"""

from datetime import date
from io import BytesIO

import requests
from config import CATALOG, get_logger
from databricks.sdk import WorkspaceClient

logger = get_logger(__name__)

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
START = (2023, 1)
TAXI_TYPES = ("yellow", "green")
NOT_PUBLISHED = (403, 404)


def months_since_start() -> list[tuple[int, int]]:
    """Every (year, month) from START up to and including the current month."""
    today = date.today()
    months = []
    year, month = START
    while (year, month) <= (today.year, today.month):
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
    for taxi in TAXI_TYPES:
        volume_dir = f"/Volumes/{CATALOG}/bronze/landing/{taxi}"
        landed = existing_files(w, volume_dir)
        for year, month in months_since_start():
            filename = f"{taxi}_tripdata_{year:04d}-{month:02d}.parquet"
            if filename in landed:
                logger.info("skip (already landed): %s", filename)
                continue
            response = requests.get(f"{BASE_URL}/{filename}", timeout=300)
            if response.status_code in NOT_PUBLISHED:
                logger.info("skip (not published yet): %s", filename)
                continue
            response.raise_for_status()
            w.files.upload(f"{volume_dir}/{filename}", BytesIO(response.content), overwrite=False)
            logger.info("downloaded: %s (%d bytes)", filename, len(response.content))


if __name__ == "__main__":
    main()
