import logging

LOG_FILENAME = "Netflix2TraktImportLog.log"
LOG_LEVEL = logging.INFO
VIEWING_HISTORY_FILENAME = "NetflixViewingHistory.csv"

# Set the datetime format of the csv file (default: %d.%m.%y for 05.02.21)
# Use %Y-%m-%d for 2021-02-05 (Canada, ...)
CSV_DATETIME_FORMAT = "%d.%m.%y"

TMDB_API_KEY = ""
TMDB_LANGUAGE = "en"
TMDB_DEBUG = False
TMDB_SYNC_STRICT = True

TRAKT_API_CLIENT_ID = ""
TRAKT_API_CLIENT_SECRET = ""
TRAKT_API_SYNC_PAGE_SIZE = 1000
