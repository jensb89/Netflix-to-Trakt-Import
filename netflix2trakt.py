#!/usr/bin/env python3

import csv
import os
import json
import logging
import config

from tenacity import retry, stop_after_attempt, wait_random
from tmdbv3api import TV, Movie, Season, TMDb
from tmdbv3api.exceptions import TMDbException
from tqdm import tqdm
from NetflixTvShow import NetflixTvHistory
from TraktIO import TraktIO
from csv import writer as csv_writer

NOT_FOUND_FILE = "not_found.csv"


class TMDBHelper:
    # Handles caching of TMDB query results to reduce API usage
    def __init__(self, cache_file="tmdb_cache.json"):
        self.cache_file = cache_file
        self.cache = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except json.JSONDecodeError:
                self.cache = {}

    def get_cached_result(self, title):
        return self.cache.get(title.lower(), None)

    def set_cached_result(self, title, result):
        self.cache[title.lower()] = result
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except TypeError:
            del self.cache[title.lower()]


def setupTMDB(tmdbKey, tmdbLanguage, tmdbDebug):
    # Configures and returns the TMDb API client
    tmdb = TMDb()
    tmdb.api_key = tmdbKey
    tmdb.language = tmdbLanguage
    tmdb.debug = tmdbDebug
    return tmdb


def setupTrakt(traktPageSize, traktDryRun):
    # Initializes the TraktIO interface
    traktIO = TraktIO(page_size=traktPageSize, dry_run=traktDryRun)
    return traktIO


def getNetflixHistory(inputFile, inputFileDelimiter):
    # Reads and parses the Netflix viewing history CSV
    netflixHistory = NetflixTvHistory()
    with open(inputFile, mode="r", encoding="utf-8") as csvFile:
        csvReader = csv.DictReader(
            csvFile, fieldnames=("Title", "Date"), delimiter=inputFileDelimiter
        )
        line_count = 0
        for row in csvReader:
            if line_count == 0:
                line_count += 1
                continue

            entry = row["Title"]
            watchedAt = row["Date"]
            logging.debug("Parsed CSV file entry: {} : {}".format(watchedAt, entry))
            netflixHistory.addEntry(entry, watchedAt)
            line_count += 1
        logging.info(f"Processed {line_count} lines.")
    return netflixHistory


def dump_uncategorized_titles(submitted_titles, response, label="sync"):
    # Logs any titles submitted that were not recognized by Trakt
    if not response:
        print("\n⚠️ No response from Trakt to categorize titles.")
        return

    known_titles = set()
    for category in ["added", "updated", "not_found"]:
        section = response.get(category, {})
        if isinstance(section, dict):
            for kind in ["movies", "episodes", "shows"]:
                entries = section.get(kind)
                if isinstance(entries, list):
                    for entry in entries:
                        title = (
                            entry.get("title")
                            or entry.get("show", {}).get("title")
                            or "UNKNOWN"
                        )
                        known_titles.add(title.lower().strip())

    unknown = [t for t in submitted_titles if t.lower().strip() not in known_titles]
    if unknown:
        print(f"\n⚠️ {len(unknown)} titles not acknowledged in Trakt response:")
        for title in unknown:
            print("  -", title)
        with open(f"uncategorized_{label}.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Unacknowledged Titles"])
            for title in unknown:
                writer.writerow([title])


@retry(stop=stop_after_attempt(5), wait=wait_random(min=2, max=10))
def getShowInformation(
    show, languageSearch, traktIO, tmdb_cache: TMDBHelper, tmdbTv=TV()
):
    # Fetches show and episode information from TMDB, adds to Trakt
    tmdbSeason = Season()
    tmdbShow = None

    if len(show.name.strip()) == 0:
        return

    try:
        cached_result = tmdb_cache.get_cached_result(show.name)
        if cached_result:
            tmdbShow = cached_result
            logging.debug(f"Cache hit for show: {show.name}")
        else:
            search_results = tmdbTv.search(show.name)
            if search_results:
                tmdbShow = search_results[0]
                tmdb_cache.set_cached_result(show.name, tmdbShow)
                logging.debug(f"Cache miss; queried TMDB for: {show.name}")
    except Exception as e:
        logging.warning("TMDB query failed for show: %s (%s)" % (show.name, e))
        return

    if not tmdbShow:
        logging.warning("Show %s not found on TMDB." % show.name)
        return

    showId = tmdbShow.get("id")
    if not showId:
        logging.warning("Could not get TMDB ID for show: %s" % show.name)
        return

    for season in show.seasons:
        tmdbResult = None
        try:
            tmdbResult = tmdbSeason.details(tv_id=showId, season_num=season.number)
        except TMDbException as e:
            logging.error(f"Error fetching season details: {e}")
            continue

        if tmdbResult and hasattr(tmdbResult, "episodes"):
            for episode in season.episodes:
                pass
        else:
            logging.warning(
                f"Could not retrieve episodes for {show.name} season {season.number}"
            )

    addShowToTrakt(show, traktIO)


def getMovieInformation(movie, strictSync, traktIO, tmdb_cache: TMDBHelper):
    # Fetches TMDB info for a movie and adds to Trakt
    tmdbMovie = Movie()
    try:
        res = tmdb_cache.get_cached_result(movie.name)
        if not res:
            search_results = tmdbMovie.search(movie.name)
            if search_results:
                res = search_results[0]
                tmdb_cache.set_cached_result(movie.name, res)

        if res:
            movie.tmdbId = res.get("id")
            logging.info(
                "Found movie %s : %s (%s)"
                % (movie.name, res.get("title"), movie.tmdbId)
            )
            addMovieToTrakt(movie, traktIO)
        else:
            logging.info("Movie not found: %s" % movie.name)
    except TMDbException as e:
        if strictSync:
            raise
        else:
            logging.info(
                "Ignoring exception while looking for movie %s: %s" % (movie.name, e)
            )


def addShowToTrakt(show, traktIO):
    # Adds each episode from a show to Trakt
    for season in show.seasons:
        logging.info(
            f"Adding episodes to trakt: {len(season.episodes)} episodes from {show.name} season {season.number}"
        )
        for episode in season.episodes:
            if episode.tmdbId:
                if traktIO.isEpisodeWatched(
                    show.name, season.number, episode.episode_number
                ):
                    logging.debug(
                        f"⏩ Skipping already-watched episode: {show.name} S{season.number}E{episode.episode_number}"
                    )
                    continue

                for watchedTime in episode.watchedAt:
                    episodeData = {
                        "watched_at": watchedTime,
                        "ids": {"tmdb": episode.tmdbId},
                    }
                    traktIO.addEpisodeToHistory(episodeData)


def addMovieToTrakt(movie, traktIO):
    # Adds a movie to Trakt
    if movie.tmdbId:
        if traktIO.isWatchedMovie(movie.tmdbId):
            logging.debug(f"⏩ Skipping already-watched movie: {movie.name}")
            return

        for watchedTime in movie.watchedAt:
            logging.info("Adding movie to trakt: %s" % movie.name)
            movieData = {
                "title": movie.name,
                "watched_at": watchedTime,
                "ids": {"tmdb": movie.tmdbId},
            }
            traktIO.addMovie(movieData)


def syncToTrakt(traktIO):
    # Final sync call to Trakt API
    try:
        logged_titles = []
        data_to_sync = traktIO.getData()

        movie_titles = [e.get("title", "UNKNOWN_MOVIE") for e in data_to_sync.get("movies", [])]
        episode_titles = [e.get("title", "UNKNOWN_EPISODE") for e in data_to_sync.get("episodes", [])]

        logged_titles.extend(movie_titles)
        logged_titles.extend(episode_titles)

        print(f"🔍 Submitting {len(logged_titles)} titles.")

        response = traktIO.sync()
        if response:
            dump_uncategorized_titles(logged_titles, response, label="sync")

            added = response.get("added", {})

            # Handle both integer and list response formats
            raw_movies = added.get("movies", 0)
            raw_episodes = added.get("episodes", 0)

            added_movies = len(raw_movies) if isinstance(raw_movies, list) else int(raw_movies)
            added_episodes = len(raw_episodes) if isinstance(raw_episodes, list) else int(raw_episodes)

            skipped_movies = len(movie_titles) - added_movies
            skipped_episodes = len(episode_titles) - added_episodes

            print(f"✅ Trakt sync complete. Added: {added_movies} movies, {added_episodes} episodes.")
            print(f"⏩ Skipped: {skipped_movies} movies, {skipped_episodes} episodes.")

    except Exception as e:
        print(f"❌ Trakt sync failed with exception: {e}")


def main():
    # Entry point: loads config, parses history, syncs Trakt
    with open(NOT_FOUND_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv_writer(f)
        writer.writerow(["Show", "Season", "Episode"])

    logging.basicConfig(filename=config.LOG_FILENAME, level=config.LOG_LEVEL)

    setupTMDB(config.TMDB_API_KEY, config.TMDB_LANGUAGE, config.TMDB_DEBUG)
    tmdb_cache = TMDBHelper()

    traktIO = setupTrakt(config.TRAKT_API_SYNC_PAGE_SIZE, config.TRAKT_API_DRY_RUN)

    netflixHistory = getNetflixHistory(
        config.VIEWING_HISTORY_FILENAME, config.CSV_DELIMITER
    )

    tv = TV()
    for show in tqdm(netflixHistory.shows, desc="Finding and adding shows to Trakt.."):
        getShowInformation(
            show, config.TMDB_EPISODE_LANGUAGE_SEARCH, traktIO, tmdb_cache, tv
        )

    for movie in tqdm(
        netflixHistory.movies, desc="Finding and adding movies to Trakt.."
    ):
        getMovieInformation(movie, config.TMDB_SYNC_STRICT, traktIO, tmdb_cache)

    syncToTrakt(traktIO)


if __name__ == "__main__":
    main()
