"""Pipeline configuration.

The target catalog is environment-driven so the same code provisions and writes
to dev or prod without changes. Free Edition is a single workspace, so we isolate
environments by Unity Catalog, not by workspace:
    nyc_tlc_dev  — default, local/testing
    nyc_tlc      — production
"""

import logging
import os

from databricks.connect import DatabricksSession

# Default to dev so an unconfigured run never touches prod.
CATALOG = os.environ.get("NYC_TLC_CATALOG", "nyc_tlc_dev")


def get_spark() -> DatabricksSession:
    """Spark session — same call locally (Databricks Connect) and on Databricks."""
    return DatabricksSession.builder.serverless(True).getOrCreate()


def get_logger(name: str) -> logging.Logger:
    """Return a logger with a shared, simple format (basicConfig is idempotent)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return logging.getLogger(name)
