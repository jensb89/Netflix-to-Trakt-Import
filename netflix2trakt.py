#!/usr/bin/env python3

import csv
import logging
import re
from time import sleep

from tenacity import retry, stop_after_attempt, wait_random
from tmdbv3api import TV, Episode, Movie, Season, TMDb
from tmdbv3api.exceptions import TMDbException
from tqdm import tqdm

import config
from NetflixTvShow import NetflixTvHistory
from TraktIO import TraktIO


def setupTMDB(tmdbKey, tmdbLanguage, tmdbDebug):
    """
    Sets up information to access TMDB.

    :param tmdbKey: API key for TMDB
    :param tmdbLanguage: Preferred language for TMDB
    :param tmdbDebug: Boolean value for debug mode
    :return: Returns `tmdb` object that contains TMDB information
    """
    tmdb = TMDb()
    tmdb.api_key = tmdbKey
    tmdb.language = tmdbLanguage
    tmdb.debug = tmdbDebug
    return tmdb


def setupTrakt(traktPageSize, traktDryRun):
    """
    Sets up Trakt information.

    :param traktPageSize: Number of items to be sync'd to Trakt at a time
    :param traktDryRun: Boolean value to determine if identified movies/TV shows are uploaded to Trakt
    :return: Returns `traktIO` object that contains Trakt information
    """
    traktIO = TraktIO(page_size=traktPageSize, dry_run=traktDryRun)
    return traktIO


def getNetflixHistory(inputFile, inputFileDelimiter):
    """
    Parses Netflix viewing history in CSV format.

    :param inputFile: File containing Netflix viewing history
    :param inputFileDelimiter: Delimiter used in Netflix viewing history (ex. CSV = `,`)
    :return: Returns `netflixHistory` that contains information parsed from viewing history CSV
    """
    # Load Netlix Viewing History and loop through every entry
    netflixHistory = NetflixTvHistory()
    with open(inputFile, mode="r", encoding="utf-8") as csvFile:
        # Make sure the file has a header "Title, Date" (first line)
        csvReader = csv.DictReader(
            csvFile, fieldnames=("Title", "Date"), delimiter=inputFileDelimiter
        )
        line_count = 0
        for row in csvReader:
            if line_count == 0:
                # Skip Header
                line_count += 1
                continue

            entry = row["Title"]
            watchedAt = row["Date"]

            logging.debug("Parsed CSV file entry: {} : {}".format(watchedAt, entry))

            # Add entry to the netflix History class to collect all shows, seasons, episodes and watch dates
            netflixHistory.addEntry(entry, watchedAt)

            line_count += 1
        logging.info(f"Processed {line_count} lines.")

        # Print result
        # logging.debug(netflixHistory.getJson())

    return netflixHistory


@retry(stop=stop_after_attempt(5), wait=wait_random(min=2, max=10))
def getShowInformation(show, tmdb, languageSearch, traktIO):
    """
    Parse TV show information,attempt to find a match on TMDB, and add it to the Trakt class object if found.

    :param show: A show that was identified when parsing Netflix viewing history
    :param tmdb: TMDB class object that contains information related to specified account
    :param languageSearch: Boolean value to look for translations of matching names
    :param traktIO: Trakt class object that holds Trakt information (API, list of shows/movies, etc.)
    """
    # Find TMDB IDs
    tmdbTv = TV()
    tmdbSeason = Season()
    tmdbEp = Episode()
    try:
        if len(show.name.strip()) != 0:
            tmdbShow = tmdbTv.search(show.name)
        if len(tmdbShow) == 0:
            logging.warning("Show %s not found on TMDB!" % show.name)

        showId = tmdbShow[0]["id"]
        details = tmdbTv.details(show_id=showId, append_to_response="")
        numSeasons = details.number_of_seasons

        for season in show.seasons:
            if season.number is None and season.name is None:
                # No season, then don't do anything
                continue

            if season.number is None and season.name is not None:
                # Try to get season number from season name
                for i in range(1, numSeasons + 1):
                    logging.debug(
                        "Requesting show %s (id %s) season %d / %d\n"
                        % (show.name, showId, int(i), int(numSeasons))
                    )
                    tmp = tmdbSeason.details(
                        tv_id=showId, season_num=i, append_to_response="translations"
                    )
                    sleep(0.1)
                    if tmp.name == season.name:
                        season.number = tmp.season_number
                        break
                if season.number is None:
                    logging.info(
                        "No season number found for %s : %s" % (show.name, season.name)
                    )
                    continue

            if season.number is not None:
                # Main loop
                logging.debug(showId)
                if int(season.number) > numSeasons:
                    season.number = numSeasons  # Netflix sometimes splits seasons that are actually one (example: Lupin)

                try:
                    tmdbResult = tmdbSeason.details(
                        tv_id=showId,
                        season_num=season.number,
                        append_to_response="translations",
                    )
                except TMDbException as err:
                    logging.error(
                        f"\nUnexpected error when searching for the season number of the show {show.name} "
                        f'by the season name "{season.name}", error at search for season {season.number}: {err}. \n'
                        "The entry will be skipped\n"
                    )
                    continue

                if languageSearch:
                    logging.info(
                        "Searching each episode individually for season %d of %s"
                        % (int(season.number), show.name)
                    )
                    for tmdbEpisode in tmdbResult.episodes:
                        try:
                            epInfo = tmdbEp.details(
                                tv_id=showId,
                                season_num=season.number,
                                episode_num=tmdbEpisode.episode_number,
                                append_to_response="translations",
                            )
                        except TMDbException as err:
                            logging.error(f"Error: {err}")
                            continue
                        for epTranslation in epInfo.translations.translations:
                            if epTranslation.iso_639_1 == tmdb.language:
                                tmdbEpisode.name = epTranslation.data.name
                        sleep(0.1)
                count = 0
                for episode in season.episodes:
                    found = False
                    for tmdbEpisode in tmdbResult.episodes:
                        # Compare TMDB episode names with Netflix Viewing History Episode name
                        logging.debug(tmdbEpisode.name)
                        if tmdbEpisode.name == episode.name:
                            episode.setTmdbId(tmdbEpisode.id)
                            episode.setEpisodeNumber(tmdbEpisode.episode_number)
                            found = True
                            count += 1
                            break
                    if not (found):
                        # Try finding episode number in the name
                        tvshowregex = re.compile(r"(?:Folge|Episode) (\d{1,2})")
                        res = tvshowregex.search(episode.name)
                        if res is not None:
                            number = int(res.group(1))
                            if number <= len(tmdbResult.episodes):
                                episode.setEpisodeNumber(number)
                                for tmdbEpisode in tmdbResult.episodes:
                                    if tmdbEpisode.episode_number == number:
                                        episode.setTmdbId(tmdbEpisode.id)
                                        count += 1
                                        found = True
                                        break

                # Try to estimate episode number from not found TMDB Names by number of episodes watched = number of episodes in season
                if len(tmdbResult.episodes) == len(season.episodes):
                    # WHole season was watched, no title names found
                    lastEpisodeNumber = len(season.episodes)
                    for episode in season.episodes:
                        if episode.tmdbId is not None:
                            lastEpisodeNumber -= 1
                            continue
                        for tmdbEpisode in tmdbResult.episodes:
                            if tmdbEpisode.episode_number == lastEpisodeNumber:
                                episode.setTmdbId(tmdbEpisode.id)
                                episode.setEpisodeNumber(tmdbEpisode.episode_number)
                                lastEpisodeNumber -= 1
                                break

                for episode in season.episodes:
                    if episode.tmdbId is None:
                        logging.info(
                            "No Tmdb ID found for %s : Season %d: %s"
                            % (show.name, int(season.number), episode.name)
                        )
                        break

        addShowToTrakt(show, traktIO)

    except TMDbException as err:
        logging.error(f"Could not add the following show to Trakt {show.name}: {err}")
    except IndexError as err:
        logging.error(f"TMDB does not contain show {show.name}: {err}")


def getMovieInformation(movie, strictSync, traktIO):
    """
    Parse movie information, attempt to find a match on TMDB, and add it to the Trakt class object if found.

    :param movie: A movie that was identified when parsing Netflix viewing history
    :param strictSync: Boolean value to determine if movie name searches should be exact matches
    :param traktIO: Trakt class object that holds Trakt information (API, list of shows/movies, etc.)
    """
    tmdbMovie = Movie()
    try:
        res = tmdbMovie.search(movie.name)
        if res:
            movie.tmdbId = res[0]["id"]
            logging.info(
                "Found movie %s : %s (%d)" % (movie.name, res[0]["title"], movie.tmdbId)
            )
            return addMovieToTrakt(movie, traktIO)

        else:
            logging.info("Movie not found: %s" % movie.name)
    except TMDbException:
        if strictSync is True:
            raise
        else:
            logging.info(
                "Ignoring appeared exception while looking for movie %s" % movie.name
            )


@retry(stop=stop_after_attempt(5), wait=wait_random(min=2, max=10))
def addShowToTrakt(show, traktIO):
    """
    Add a show to the Trakt class object.

    :param show: A show that was identified when parsing Netflix viewing history
    :param traktIO: Trakt class object that holds Trakt information (API, list of shows/movies, etc.)
    """
    for season in show.seasons:
        logging.info(
            f"Adding episodes to trakt: {len(season.episodes)} episodes from {show.name} season {season.number}"
        )
        for episode in season.episodes:
            if episode.tmdbId is not None:
                for watchedTime in episode.watchedAt:
                    episodeData = {
                        "watched_at": watchedTime,
                        "ids": {"tmdb": episode.tmdbId},
                    }
                    traktIO.addEpisodeToHistory(episodeData)


@retry(stop=stop_after_attempt(5), wait=wait_random(min=2, max=10))
def addMovieToTrakt(movie, traktIO):
    """
    Add a movie to the Trakt class object.

    :param movie: A movie that was identified when parsing Netflix viewing history
    :param traktIO: Trakt class object that holds Trakt information (API, list of shows/movies, etc.)
    """
    if movie.tmdbId is not None:
        for watchedTime in movie.watchedAt:
            logging.info("Adding movie to trakt: %s" % movie.name)
            movieData = {
                "title": movie.name,
                "watched_at": watchedTime,
                "ids": {"tmdb": movie.tmdbId},
            }
            traktIO.addMovie(movieData)
            return traktIO


@retry(stop=stop_after_attempt(5), wait=wait_random(min=2, max=10))
def syncToTrakt(traktIO):
    """
    Sync information that was added to the Trakt class object.

    :param traktIO: Trakt class object that holds Trakt information (API, list of shows/movies, etc.)
    """
    try:
        traktIO.sync()
    except Exception:
        pass


def main():
    """
    Main function that pulls information from config.ini to parse Netflix viewing history and adds identified matches on TMDB to Trakt.
    """
    # Setup logging
    logging.basicConfig(filename=config.LOG_FILENAME, level=config.LOG_LEVEL)

    # Connect to TMDB
    tmdb = setupTMDB(config.TMDB_API_KEY, config.TMDB_LANGUAGE, config.TMDB_DEBUG)

    # Setup trakt and sync to trakt
    traktIO = setupTrakt(config.TRAKT_API_SYNC_PAGE_SIZE, config.TRAKT_API_DRY_RUN)
    traktIO.init()

    # Parse Netflix History file
    netflixHistory = getNetflixHistory(
        config.VIEWING_HISTORY_FILENAME, config.CSV_DELIMITER
    )

    # Get show information
    for show in tqdm(netflixHistory.shows, desc="Finding and adding shows to Trakt.."):
        getShowInformation(show, tmdb, config.TMDB_EPISODE_LANGUAGE_SEARCH, traktIO)

    # Get movie information
    for movie in tqdm(
        netflixHistory.movies, desc="Finding and adding movies to Trakt.."
    ):
        getMovieInformation(movie, config.TMDB_SYNC_STRICT, traktIO)

    # Sync to Trakt
    syncToTrakt(traktIO)


if __name__ == "__main__":
    main()
