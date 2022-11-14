import datetime
import logging
import re

import config

# Setup logging
logging.basicConfig(filename=config.LOG_FILENAME, level=config.LOG_LEVEL)


class NetflixTvHistory(object):
    def __init__(self):
        self.shows = []
        self.movies = []

    def hasTvShow(self, showName):
        return self.getTvShow(showName) is not None

    def getTvShow(self, showName):
        """
        Get the tv show with name showName
        :param showName:
        :return the found tv show or None:
        """
        for show in self.shows:
            if show.name == showName:
                return show
        return None

    def getMovie(self, movieName):
        for movie in self.movies:
            if movie.name == movieName:
                return movie
        return None

    def addEntry(self, entryTitle, entryDate):
        # check for a pattern TvShow : Season 1: EpisodeTitle
        tvshowregex = re.compile(r"(.+): .+ (\d{1,2}): (.*)")
        res = tvshowregex.search(entryTitle)
        if res is not None:
            # found tv show
            showName = res.group(1)
            seasonNumber = res.group(2)
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
            seasonNumber = res.group(2)
            episodeTitle = res.group(3)
            self.addTvShowEntry(showName, seasonNumber, episodeTitle, entryDate)
            return True

        # Check for TvShow : TvShow : Miniseries : EpisodeTitle
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
            self.addTvShowEntry(showName, None, episodeTitle, entryDate, seasonName=seasonName)
            return True

        # Else the entry is a movie
        self.addMovieEntry(entryTitle, entryDate)

    def addTvShowEntry(self, showName, seasonNumber, episodeTitle, watchedDate, seasonName=None):
        show = self.addTvShow(showName)
        season = show.addSeason(seasonNumber=seasonNumber, seasonName=seasonName)
        episode = season.addEpisode(episodeTitle)
        episode.addWatchedDate(watchedDate)
        logging.info(
            "Added show %s season %d episode %s"
            % (show.name, int(season.number) if season.number is not None else -1, episode.name)
        )

    def addTvShow(self, showName):
        show = self.getTvShow(showName)
        if show is not None:
            return show
        else:
            self.shows.append(NetflixTvShow(showName))
            return self.shows[-1]

    def addMovieEntry(self, movieTitle, watchedDate):
        movie = self.getMovie(movieTitle)
        if movie is not None:
            movie.addWatchedDate(watchedDate)
            return movie
        else:
            self.movies.append(NetflixMovie(movieTitle))
            movie = self.movies[-1]
            movie.addWatchedDate(watchedDate)
            return movie

    def getJson(self):
        jsonOut = {"tvshows": {}, "movies": {}}
        for show in self.shows:
            jsonOut["tvshows"][show.name] = []
            for season in show.seasons:
                jsonOut["tvshows"][show.name].append(
                    {"SeasonNumber": season.number, "SeasonName": season.name, "episodes": {}}
                )
                for episode in season.episodes:
                    jsonOut["tvshows"][show.name][-1]["episodes"][episode.name] = []
                    for watchedAt in episode.watchedAt:
                        jsonOut["tvshows"][show.name][-1]["episodes"][episode.name].append(watchedAt)
        for movie in self.movies:
            jsonOut["movies"][movie.name] = []
            for watchedAt in movie.watchedAt:
                jsonOut["movies"][movie.name].append(watchedAt)
        return jsonOut


class NetflixWatchableItem(object):
    def __init__(self, name):
        self.name = name
        # watchedAt is a set to prevent duplicate entries
        self._watchedAt = set()

    @property
    def watchedAt(self):
        return list(self._watchedAt)

    def addWatchedDate(self, watchedDate):
        try:
            # Netflix exports only have the date. Add an arbitrary time.
            time = datetime.datetime.strptime(watchedDate + " 20:15", config.CSV_DATETIME_FORMAT + " %H:%M")
        except ValueError:
            # try the date with a dot (also for backwards compatbility)
            watchedDate = re.sub("[^0-9]", ".", watchedDate)
            time = datetime.datetime.strptime(watchedDate + " 20:15", "%m.%d.%y %H:%M")
        return self._watchedAt.add(time.strftime("%Y-%m-%dT%H:%M:%S.00Z"))


class NetflixMovie(NetflixWatchableItem):
    def __init__(self, movieName):
        super().__init__(movieName)
        self.tmdbId = None


class NetflixTvShow(object):
    def __init__(self, showName):
        self.name = showName
        self.seasons = []

    def addSeason(self, seasonNumber, seasonName=None):
        season = self.getSeasonByNumber(seasonNumber)
        if season is not None:
            return season
        season = self.getSeasonByName(seasonName)
        if season is not None:
            return season

        self.seasons.append(NetflixTvShowSeason(seasonNumber, seasonName))
        return self.seasons[-1]

    def getSeasonByNumber(self, seasonNumber):
        for season in self.seasons:
            if season.number == seasonNumber:
                return season
        return None

    def getSeasonByName(self, seasonName):
        for season in self.seasons:
            if season.name == seasonName and season.name is not None:
                return season
        return None


class NetflixTvShowSeason(object):
    def __init__(self, seasonNumber, seasonName=None):
        self.number = seasonNumber
        self.name = seasonName
        self.episodes = []

    def addEpisode(self, episodeName):
        episode = self.getEpisodeByName(episodeName)
        if episode is not None:
            return episode

        self.episodes.append(NetflixTvShowEpisode(episodeName))
        return self.episodes[-1]

    def getEpisodeByName(self, episodeName):
        for episode in self.episodes:
            if episode.name == episodeName:
                return episode
        return None


class NetflixTvShowEpisode(NetflixWatchableItem):
    def __init__(self, episodeName):
        super().__init__(episodeName)
        self.tmdbId = None
        self.number = None

    def setEpisodeNumber(self, number):
        self.number = number

    def setTmdbId(self, id):
        self.tmdbId = id
