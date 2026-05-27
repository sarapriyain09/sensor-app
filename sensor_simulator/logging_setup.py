from __future__ import annotations

import logging


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application logging to stdout."""

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
