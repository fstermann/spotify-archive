import logging
import sys

logger = logging.getLogger("spotify-archive")
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(fmt="%(asctime)s : %(levelname)s : %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
