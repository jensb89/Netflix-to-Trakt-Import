import logging

LOG_FILENAME = "Netflix2TraktImportLog.log"
LOG_LEVEL = logging.INFO
VIEWING_HISTORY_FILENAME = "NetflixViewingHistory.csv"

# Set the datetime format of the csv file and the delimiter (default: %d.%m.%y for 05.02.21 and "," as delimiter between date and entry)
# Use %Y-%m-%d for 2021-02-05 (Canada, ...)
# For the format 17.05.2023 use the datetime format %d.%m.%Y (note the capital Y for 2023 instead of y for 23)
CSV_DATETIME_FORMAT = "%d.%m.%y"
CSV_DELIMITER = "," #delimiter between the entries (like "," between '"Push","28.02.23"')

TMDB_API_KEY = ""
TMDB_LANGUAGE = "en"
TMDB_DEBUG = False
TMDB_SYNC_STRICT = True
TMDB_EPISODE_LANGUAGE_SEARCH = False # more api calls, longer waiting time, 
                                     # only useful if the tmdb language differs from en 
                                     # and episodes cannot be found in the season overview Api calls

TRAKT_API_CLIENT_ID = ""
TRAKT_API_CLIENT_SECRET = ""
TRAKT_API_DRY_RUN = False
TRAKT_API_SYNC_PAGE_SIZE = 1000
