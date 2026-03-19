"""notetrans - HackMD to Obsidian Markdown exporter."""

import logging

__version__ = "0.1.0"

logger = logging.getLogger("notetrans")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

# Default format: simple, CLI-friendly
_handler = logger.handlers[0]
_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
