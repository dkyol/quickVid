"""Clean, consistent logging for the whole package.

One call to `setup_logging()` at program start; everything else just does
`log = logging.getLogger(__name__)`. Keeps console output readable and
optionally tees to a per-run logfile under the project's logs/ dir.
"""

import logging
import os
import sys
from datetime import datetime


def setup_logging(level=logging.INFO, logfile_dir=None):
    """Configure root logging. If `logfile_dir` is given, also write a
    timestamped logfile there (created if missing)."""
    handlers = [logging.StreamHandler(sys.stdout)]
    if logfile_dir:
        os.makedirs(logfile_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        handlers.append(logging.FileHandler(
            os.path.join(logfile_dir, f"run_{stamp}.log"), encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,  # replace any prior config so re-runs stay clean
    )
    # Quiet noisy third-party loggers.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    return logging.getLogger("carvegen")
