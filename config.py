import configparser
import logging
import sys


class Section(object):
    LOGGING = "Logging"
    NETFLIX = "Netflix"
    TMDB = "TMDB"
    TRAKT = "Trakt"


_config = configparser.ConfigParser()
_config.read("config_defaults.ini")

# optional user configs go in config.ini
# ignore them if we're running tests
if "pytest" not in sys.modules:  # pragma: no cover
    _config.read("config.ini")

LOG_FILENAME = _config.get(Section.LOGGING, "filename")
LOG_LEVEL = logging.getLevelName(_config.get(Section.LOGGING, "level"))

VIEWING_HISTORY_FILENAME = _config.get(Section.NETFLIX, "viewing_history_filename")
CSV_DATETIME_FORMAT = _config.get(Section.NETFLIX, "viewing_history_datetime_format")
CSV_DELIMITER = _config.get(Section.NETFLIX, "viewing_history_delimiter")

TMDB_API_KEY = _config.get(Section.TMDB, "api_key")
TMDB_LANGUAGE = _config.get(Section.TMDB, "language")
TMDB_DEBUG = _config.getboolean(Section.TMDB, "debug")
TMDB_SYNC_STRICT = _config.getboolean(Section.TMDB, "strict")
TMDB_EPISODE_LANGUAGE_SEARCH = _config.getboolean(
    Section.TMDB, "episode_language_search"
)

TRAKT_API_CLIENT_ID = _config.get(Section.TRAKT, "id")
TRAKT_API_CLIENT_SECRET = _config.get(Section.TRAKT, "secret")
TRAKT_API_DRY_RUN = _config.getboolean(Section.TRAKT, "dry_run")
TRAKT_API_SYNC_PAGE_SIZE = _config.getint(Section.TRAKT, "page_size")
