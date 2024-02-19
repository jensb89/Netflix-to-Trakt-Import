import datetime
import logging
import re
from typing import Optional, Set, Union

import config

# Setup logging
logging.basicConfig(filename=config.LOG_FILENAME, level=config.LOG_LEVEL)

# A class that stores all the shows and movies that you have watched on Netflix.
class NetflixTvHistory(object):
    def __init__(self):
        self.shows = []
        self.movies = []

    def hasTvShow(self, showName: str) -> bool:
        """
        Returns `True` if the show exists in the database, `False` otherwise
        :param showName: The name of the show you want to check for
        :type showName: str
        :return: A boolean value.
        """
        return self.getTvShow(showName) is not None

    def getTvShow(self, showName: str):
        """
        Get the tv show with name showName
        :param showName:
        :return the found tv show or None:
        """
        for show in self.shows:
            if show.name == showName:
                return show
        return None

    def getMovie(self, movieName: str):
        """
        It returns the movie object with the name movieName
        :param movieName: The name of the movie you want to get
        :type movieName: str
        :return: A movie object
        """
        for movie in self.movies:
            if movie.name == movieName:
                return movie
        return None

    def addEntry(self, entryTitle: str, entryDate: str) -> bool:
        """
        It takes a string and tries to find a pattern that matches a TV show. If it finds one, it adds
        the TV show to the history list. If it doesn't find one, it adds the string as a movie

        :param entryTitle: The title of the entry
        :type entryTitle: str
        :param entryDate: The date the entry was watched
        :type entryDate: str
        :return: A list of tuples.
        """

        # check for a pattern TvShow : Season 1: EpisodeTitle
        tvshowregex = re.compile(r"(.+): .+ (\d{1,2}): (.*)")
        res = tvshowregex.search(entryTitle)
        if res is not None:
            # found tv show
            showName = res.group(1)
            seasonNumber = int(res.group(2))
            episodeTitle = res.group(3)
            self.addTvShowEntry(showName, seasonNumber, episodeTitle, entryDate)
            return True

        # Check for TvShow : Season 1 - Part A: EpisodeTitle
        # Example: Die außergewoehnlichsten Haeuser der Welt: Staffel 2 – Teil B: Spanien
        tvshowregex = re.compile(r"(.+): .+ (\d{1,2}) – .+: (.*)")
        res = tvshowregex.search(entryTitle)
        if res is not None:
            # found tv show
            showName = res.group(1)
            seasonNumber = int(res.group(2))
            episodeTitle = res.group(3)
            self.addTvShowEntry(showName, seasonNumber, episodeTitle, entryDate)
            return True

        # Check for TvShow : TvShow: Miniseries : EpisodeTitle
        tvshowregex = re.compile(r"(.+): \w+: (.+)")
        res = tvshowregex.search(entryTitle)
        if res is not None:
            showName = res.group(1)
            seasonNumber = 1
            episodeTitle = res.group(2)
            self.addTvShowEntry(showName, seasonNumber, episodeTitle, entryDate)
            return True

        # Check for TvShow: SeasonName : EpisodeTitle
        # Example: American Horror Story: Murder House: Nachgeburt
        tvshowregex = re.compile(r"(.+): (.+): (.+)")
        res = tvshowregex.search(entryTitle)
        if res is not None:
            showName = res.group(1)
            seasonName = res.group(2)
            episodeTitle = res.group(3)
            self.addTvShowEntry(
                showName, None, episodeTitle, entryDate, seasonName=seasonName
            )
            return True

        # Check for TvShow: EpisodeTitle
        # sometimes used in this format for the first season of a show
        # Example: "Wednesday: Leid pro quo","29.11.22"
        # @tricky: Also movies sometimes use this format (e.g "King Arthur: Legend of the Sword","17.01.21")
        tvshowregex = re.compile(r"(.+): (.+)")
        res = tvshowregex.search(entryTitle)
        if res is not None:
            showName = res.group(1)
            seasonNumber = 1
            episodeTitle = res.group(2)
            self.addTvShowEntry(showName, seasonNumber, episodeTitle, entryDate)
            # no return here in order to add it also as a movie (as it can have the same format)

        # Else the entry is a movie
        self.addMovieEntry(entryTitle, entryDate)
        return True

    def addTvShowEntry(
        self,
        showName: str,
        seasonNumber: Union[int, None],
        episodeTitle: str,
        watchedDate: str,
        seasonName: Optional[str] = None,
    ) -> None:
        """
        It adds a TV show, season, episode, and watched date to the history list

        :param showName: The name of the show
        :type showName: str
        :param seasonNumber: The season number
        :type seasonNumber: Union[int,None]
        :param episodeTitle: The title of the episode
        :type episodeTitle: str
        :param watchedDate: The date the episode was watched
        :type watchedDate: str
        :param seasonName: The name of the season, if it has one
        :type seasonName: Optional[str]
        """
        show = self.addTvShow(showName)
        season = show.addSeason(seasonNumber=seasonNumber, seasonName=seasonName)
        episode = season.addEpisode(episodeTitle)
        episode.addWatchedDate(watchedDate)

    def addTvShow(self, showName):
        """
        It adds a tv show to the list of shows.

        :param showName: The name of the show you want to add
        :return: The last item in the list of shows.
        """
        show = self.getTvShow(showName)
        if show is not None:
            return show
        else:
            self.shows.append(NetflixTvShow(showName))
            return self.shows[-1]

    def addMovieEntry(self, movieTitle, watchedDate):
        """
        It adds a movie to the list of movies and adds the date it was watched to the movie.

        :param movieTitle: The title of the movie you want to add
        :param watchedDate: a string in the format "YYYY-MM-DD" or similar (as given in the config)
        :return: The movie object that was just added to the list of movies.
        """
        movie = self.getMovie(movieTitle)
        if movie is not None:
            movie.addWatchedDate(watchedDate)
            return movie
        else:
            self.movies.append(NetflixMovie(movieTitle))
            movie = self.movies[-1]
            movie.addWatchedDate(watchedDate)
            return movie

    def getJson(self) -> dict:
        """
        It takes the data from the objects and puts it into a dictionary
        :return: A dictionary with two keys, "tvshows" and "movies".
        """
        jsonOut: dict = {"tvshows": {}, "movies": {}}
        for show in self.shows:
            jsonOut["tvshows"][show.name] = []
            for season in show.seasons:
                jsonOut["tvshows"][show.name].append(
                    {
                        "SeasonNumber": season.number,
                        "SeasonName": season.name,
                        "episodes": {},
                    }
                )
                for episode in season.episodes:
                    jsonOut["tvshows"][show.name][-1]["episodes"][episode.name] = []
                    for watchedAt in episode.watchedAt:
                        jsonOut["tvshows"][show.name][-1]["episodes"][
                            episode.name
                        ].append(watchedAt)
        for movie in self.movies:
            jsonOut["movies"][movie.name] = []
            for watchedAt in movie.watchedAt:
                jsonOut["movies"][movie.name].append(watchedAt)
        return jsonOut


# A class that represents a Netflix watchable item
class NetflixWatchableItem(object):
    def __init__(self, name: str):
        self.name = name
        # watchedAt is a set to prevent duplicate entries
        self._watchedAt: Set[str] = set()

    @property
    def watchedAt(self):
        return list(self._watchedAt)

    def addWatchedDate(self, watchedDate: str):
        try:
            # Netflix exports only have the date. Add an arbitrary time.
            time = datetime.datetime.strptime(
                watchedDate + " 20:15", config.CSV_DATETIME_FORMAT + " %H:%M"
            )
        except ValueError:
            # try the date with a dot (also for backwards compatbility)
            watchedDate = re.sub("[^0-9]", ".", watchedDate)
            time = datetime.datetime.strptime(watchedDate + " 20:15", "%m.%d.%y %H:%M")
        return self._watchedAt.add(time.strftime("%Y-%m-%dT%H:%M:%S.00Z"))


# The `NetflixMovie` class is a subclass of the `NetflixWatchableItem` class
class NetflixMovie(NetflixWatchableItem):
    def __init__(self, movieName: str):
        super().__init__(movieName)
        self.tmdbId = None


# `NetflixTvShowEpisode` is a `NetflixWatchableItem` that has a `tmdbId` and a `number`
class NetflixTvShowEpisode(NetflixWatchableItem):
    def __init__(self, episodeName: str):
        super().__init__(episodeName)
        self.tmdbId = None
        self.number: Union[int, None] = None

    def setEpisodeNumber(self, number: Union[int, None]):
        """
        Sets the episode number

        :param number: The episode number
        :type number: Union[int, None]
        """
        self.number = number

    def setTmdbId(self, id):
        """
        Sets the tmdbId of the episode
        :param id: The ID of the episode
        """
        self.tmdbId = id


# A NetflixTvShowSeason is a season of a tv show, and it has a number, a name, and a list of episodes
class NetflixTvShowSeason(object):
    def __init__(self, seasonNumber: int, seasonName: Optional[str] = None):
        self.number: int = seasonNumber
        self.name: Optional[str] = seasonName
        self.episodes: list[NetflixTvShowEpisode] = []

    def addEpisode(self, episodeName: str):
        """
        If the episode already exists, return it. Otherwise, add it to the list of episodes and return it

        :param episodeName: The name of the episode
        :type episodeName: str
        :return: The last episode in the list of episodes.
        """
        episode = self.getEpisodeByName(episodeName)
        if episode is not None:
            return episode

        self.episodes.append(NetflixTvShowEpisode(episodeName))
        return self.episodes[-1]

    def getEpisodeByName(self, episodeName: str):
        """
        Returns the episode with the given name.

        :param episodeName: The name of the episode you want to get
        :type episodeName: str
        :return: The episode if it was found, otherwise None
        """
        for episode in self.episodes:
            if episode.name == episodeName:
                return episode
        return None


# The NetflixTvShow class represents a TV show on Netflix. It has a name, and a list of seasons
class NetflixTvShow(object):
    def __init__(self, showName: str):
        self.name: str = showName
        self.seasons: list[NetflixTvShowSeason] = []

    def addSeason(self, seasonNumber: int, seasonName: str) -> NetflixTvShowSeason:
        """
        If the season doesn't exist, add it to the list of seasons

        :param seasonNumber: The season number of the season
        :type seasonNumber: int
        :param seasonName: The name of the season
        :type seasonName: str
        :return: The last season added to the list of seasons
        """
        season = self.getSeasonByNumber(seasonNumber)
        if season is not None:
            return season
        season = self.getSeasonByName(seasonName)
        if season is not None:
            return season

        self.seasons.append(NetflixTvShowSeason(seasonNumber, seasonName))
        return self.seasons[-1]

    def getSeasonByNumber(self, seasonNumber: int) -> Union[NetflixTvShowSeason, None]:
        """
        "Return the season with the given number, or None if no such season exists."

        :param seasonNumber: The season number you want to get
        :type seasonNumber: int
        :return: A NetflixTvShowSeason object or None
        """
        for season in self.seasons:
            if season.number == seasonNumber:
                return season
        return None

    def getSeasonByName(self, seasonName: str) -> Union[NetflixTvShowSeason, None]:
        """
        Returns a season object from the seasons list if the name of the season matches the
        name passed to the function, otherwise none

        :param seasonName: The name of the season you want to get
        :type seasonName: str
        :return: A NetflixTvShowSeason object or None
        """
        for season in self.seasons:
            if season.name == seasonName and season.name is not None:
                return season
        return None
