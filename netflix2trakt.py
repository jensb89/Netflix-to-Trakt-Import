#!/usr/bin/python3

import csv
import datetime
import logging
import re
from time import sleep

from tmdbv3api import TV, Movie, Season, TMDb
from tmdbv3api.exceptions import TMDbException

import config
from NetflixTvShow import NetflixTvHistory
from TraktIO import TraktIO

# Setup logging
logging.basicConfig(filename=config.LOG_FILENAME, level=config.LOG_LEVEL)

# Connect to TMDB
tmdb = TMDb()
tmdb.api_key = config.TMDB_API_KEY
tmdb.language = config.TMDB_LANGUAGE
tmdb.debug = config.TMDB_DEBUG

# Load Netlix Viewing History and loop through every entry
netflixHistory = NetflixTvHistory()
with open(config.VIEWING_HISTORY_FILENAME, mode="r", encoding="utf-8") as csvFile:
    # Make sure the file has a header "Title, Date" (first line)
    csvReader = csv.DictReader(csvFile, fieldnames=("Title", "Date"))
    line_count = 0
    for row in csvReader:
        if line_count == 0:
            # Skip Header
            line_count += 1
            continue

        entry = row["Title"]
        watchedAt = row["Date"]

        # Add entry to the netflix History class to collect all shows, seasons, episodes and watch dates
        netflixHistory.addEntry(entry, watchedAt)

        line_count += 1
    logging.info(f"Processed {line_count} lines.")

# Print result
logging.debug(netflixHistory.getJson())

# Find TMDB IDs
tmdbTv = TV()
tmdbSeason = Season()
for show in netflixHistory.shows:
    logging.info("Searching %s" % show.name)
    tmdbShow = tmdbTv.search(show.name)
    if len(tmdbShow) == 0:
        logging.warning("Show %s not found on TMDB!" % show.name)
        continue
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
                tmp = tmdbSeason.details(tv_id=showId, season_num=i, append_to_response="translations")
                sleep(0.1)
                if tmp.name == season.name:
                    season.number = tmp.season_number
                    logging.info(
                        "Found season for show with only season name (%s : %d - %s)"
                        % (show.name, season.number, season.name)
                    )
                    break
            if season.number is None:
                logging.info("No season number found for %s : %s" % (show.name, season.name))
                continue

        if season.number is not None:
            # Main loop
            logging.debug(showId)
            if int(season.number) > numSeasons:
                season.number = numSeasons  # Netflix sometimes splits seasons that are actually one (example: Lupin)
            tmdbResult = tmdbSeason.details(tv_id=showId, season_num=season.number, append_to_response="translations")
            count = 0
            for episode in season.episodes:
                found = False
                for tmdbEpisode in tmdbResult.episodes:
                    # Compare TMDB episode names with Netflix Viewing History Episode name
                    logging.debug(tmdbEpisode.name)
                    if tmdbEpisode.name == episode.name:
                        episode.setTmdbId(tmdbEpisode.id)
                        episode.setEpisodeNumber(tmdbEpisode.episode_number)
                        logging.info(
                            "Found Tmdb ID for %s : Season %d: %s (TMDB ID %d)"
                            % (show.name, int(season.number), episode.name, tmdbEpisode.id)
                        )
                        print(
                            "Found Tmdb ID for %s : Season %d: %s (TMDB ID %d)"
                            % (show.name, int(season.number), episode.name, tmdbEpisode.id)
                        )
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
                                    logging.info(
                                        "Found Tmdb ID (by name) for %s : Season %d: %s (TMDB ID %d - %s Episode %d)"
                                        % (
                                            show.name,
                                            int(season.number),
                                            episode.name,
                                            tmdbEpisode.id,
                                            tmdbEpisode.name,
                                            tmdbEpisode.episode_number,
                                        )
                                    )
                                    print(
                                        "Found Tmdb ID (by name) for %s : Season %d: %s (TMDB ID %d - %s Episode %d)"
                                        % (
                                            show.name,
                                            int(season.number),
                                            episode.name,
                                            tmdbEpisode.id,
                                            tmdbEpisode.name,
                                            tmdbEpisode.episode_number,
                                        )
                                    )

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
                            logging.info(
                                "Found Tmdb ID (by estimate) for %s : Season %d: %s (TMDB ID %d - %s Episode %d)"
                                % (
                                    show.name,
                                    int(season.number),
                                    episode.name,
                                    tmdbEpisode.id,
                                    tmdbEpisode.name,
                                    tmdbEpisode.episode_number,
                                )
                            )
                            print(
                                "Found Tmdb ID (by estimate) for %s : Season %d: %s (TMDB ID %d - %s Episode %d)"
                                % (
                                    show.name,
                                    int(season.number),
                                    episode.name,
                                    tmdbEpisode.id,
                                    tmdbEpisode.name,
                                    tmdbEpisode.episode_number,
                                )
                            )
                            break

            for episode in season.episodes:
                if episode.tmdbId is None:
                    logging.info(
                        "No Tmdb ID found for %s : Season %d: %s" % (show.name, int(season.number), episode.name)
                    )
                    print("No Tmdb ID found for %s : Season %d: %s" % (show.name, int(season.number), episode.name))

        sleep(0.2)

tmdbMovie = Movie()
for movie in netflixHistory.movies:
    try:
        res = tmdbMovie.search(movie.name)
        if res:
            movie.tmdbId = res[0]["id"]
            print("Found movie %s : %s (%d)" % (movie.name, res[0]["title"], movie.tmdbId))
            logging.info("Found movie %s : %s (%d)" % (movie.name, res[0]["title"], movie.tmdbId))
        else:
            print("Movie not found: %s" % movie.name)
            logging.info("Movie not found %s" % movie.name)
    except TMDbException:
        if config.TMDB_SYNC_STRICT is True:
            raise
        else:
            print("Ignoring appeared exception while looking for movie %s" % movie.name)
            logging.info("Ignoring appeared exception while looking for movie %s" % movie.name)


logging.info(netflixHistory.getJson())


# Sync to trakt
traktIO = TraktIO()
traktIO.init()
for show in netflixHistory.shows:
    for season in show.seasons:
        for episode in season.episodes:
            if episode.tmdbId is not None:
                print("Adding epsiode to trakt:")
                for watchedTime in episode.watchedAt:
                    try:
                        time = datetime.datetime.strptime(watchedTime + " 20:15", config.CSV_DATETIME_FORMAT + " %H:%M")
                    except ValueError:
                        # try the date with a dot (also for backwards compatbility)
                        watchedTime = re.sub("[^0-9]", ".", watchedTime)
                        time = datetime.datetime.strptime(watchedTime + " 20:15", config.CSV_DATETIME_FORMAT + " %H:%M")
                    addInfo = {
                        "episodes": [
                            {"watched_at": time.strftime("%Y-%m-%dT%H:%M:%S.00Z"), "ids": {"tmdb": episode.tmdbId}}
                        ]
                    }
                    print(addInfo)
                    ret = traktIO.addEpisodeToHistory(addInfo)
                    # print(ret) # Todo: Check if epsiode was really added by checking for ret["added"]["epsiodes"] == 1
                    # Trakt API Rate limit: 1 POST call per second
                    sleep(1.2)

for movie in netflixHistory.movies:
    if movie.tmdbId is not None:
        for watchedTime in movie.watchedAt:
            print("Adding movie to trakt:")
            watchedTime = re.sub("[^0-9]", ".", watchedTime)
            time = datetime.datetime.strptime(watchedTime + " 20:15", config.CSV_DATETIME_FORMAT + " %H:%M")
            addInfo = {
                "movies": [
                    {
                        "title": movie.name,
                        "watched_at": time.strftime("%Y-%m-%dT%H:%M:%S.00Z"),
                        "ids": {"tmdb": movie.tmdbId},
                    }
                ]
            }
            print(addInfo)
            ret = traktIO.addMovie(addInfo)
            # print(ret) # Todo: Check if movie was really added by checking for ret["added"]["movies"] == 1
            sleep(1.2)
