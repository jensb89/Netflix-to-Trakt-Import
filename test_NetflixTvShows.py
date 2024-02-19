import unittest
from datetime import datetime

from NetflixTvShow import NetflixTvHistory, NetflixTvShow


def test_addSingleTvShow():
    """Test to add a single episode and check if all information is correctly parsed"""
    netflixHistory = NetflixTvHistory()
    ret = netflixHistory.addEntry(
        "Peaky Blinders – Gangs of Birmingham: Staffel 1: Geschenk des Teufels",
        "03.10.21",
    )
    assert ret is not False
    assert netflixHistory.hasTvShow("Peaky Blinders – Gangs of Birmingham")
    assert netflixHistory.shows[0].name == "Peaky Blinders – Gangs of Birmingham"
    assert int(netflixHistory.shows[0].seasons[0].number) == 1
    assert netflixHistory.shows[0].seasons[0].name is None
    assert (
        netflixHistory.shows[0].seasons[0].episodes[0].watchedAt[0]
        == "2021-10-03T20:15:00.00Z"
    )


def test_addMultipleTvShows():
    """Test to add 3 episodes of 2 different shows and check that both shows and number of episodes are correct"""
    netflixHistory = NetflixTvHistory()
    ret1 = netflixHistory.addEntry(
        "Peaky Blinders – Gangs of Birmingham: Staffel 1: Geschenk des Teufels",
        "03.10.21",
    )
    ret2 = netflixHistory.addEntry("Haus des Geldes: Teil 5: Wunschdenken", "03.12.21")
    ret3 = netflixHistory.addEntry(
        "Haus des Geldes: Teil 5: Sicherheitsventil", "03.12.21"
    )
    assert ret1 is ret2 is ret3 is True
    assert netflixHistory.hasTvShow("Peaky Blinders – Gangs of Birmingham") is True
    assert netflixHistory.hasTvShow("Haus des Geldes")
    assert (
        len(netflixHistory.getTvShow("Haus des Geldes").getSeasonByNumber(5).episodes)
        == 2
    )


def test_addMovie():
    """Test to add a movie and check if it was recoginzied as a movie"""
    netflixHistory = NetflixTvHistory()
    netflixHistory.addEntry("Spider-Man: Far from Home", "16.09.21")
    assert netflixHistory.getMovie("Spider-Man: Far from Home") is not None
    assert netflixHistory.movies[0].watchedAt[0] == "2021-09-16T20:15:00.00Z"


class TestNetflixTvHistory(unittest.TestCase):
    def setUp(self):
        self.history = NetflixTvHistory()

    def test_getTvShow(self):
        self.assertIsNone(self.history.getTvShow("Stranger Things"))

        showName = "Breaking Bad"
        show = NetflixTvShow(showName)
        self.history.shows.append(show)

        self.assertEqual(self.history.getTvShow(showName), show)
        self.assertIsNone(self.history.getTvShow("The Office"))

    def test_addEntry_tvshow_regex1(self):
        entryTitle = "Breaking Bad: Season 3: Fly"
        entryDate = datetime.now()
        self.history.addEntry(entryTitle, entryDate.strftime("%d.%m.%y"))

        show = self.history.getTvShow("Breaking Bad")
        self.assertIsNotNone(show)

        season = show.getSeasonByNumber(3)
        self.assertIsNotNone(season)

        episode = season.getEpisodeByName("Fly")
        self.assertIsNotNone(episode)
        self.assertIn(
            entryDate.replace(hour=20, minute=15, second=0).strftime(
                "%Y-%m-%dT%H:%M:%S.00Z"
            ),
            episode.watchedAt,
        )

    def test_addEntry_tvshow_regex2(self):
        entryTitle = (
            "Die außergewoehnlichsten Haeuser der Welt: Staffel 2 – Teil B: Spanien"
        )
        entryDate = datetime.now()
        self.history.addEntry(entryTitle, entryDate.strftime("%d.%m.%y"))

        show = self.history.getTvShow("Die außergewoehnlichsten Haeuser der Welt")
        self.assertIsNotNone(show)

        season = show.getSeasonByNumber(2)
        self.assertIsNotNone(season)

        episode = season.getEpisodeByName("Spanien")
        self.assertIsNotNone(episode)
        self.assertIn(
            entryDate.replace(hour=20, minute=15, second=0).strftime(
                "%Y-%m-%dT%H:%M:%S.00Z"
            ),
            episode.watchedAt,
        )

    def test_addEntry_tvshow_regex3(self):
        entryTitle = "The Falcon and The Winter Soldier: Miniseries: Episode 6"
        entryDate = datetime.now()
        self.history.addEntry(entryTitle, entryDate.strftime("%d.%m.%y"))

        show = self.history.getTvShow("The Falcon and The Winter Soldier")
        self.assertIsNotNone(show)

        season = show.getSeasonByNumber(1)
        self.assertIsNotNone(season)

        episode = season.getEpisodeByName("Episode 6")
        self.assertIsNotNone(episode)
        self.assertIn(
            entryDate.replace(hour=20, minute=15, second=0).strftime(
                "%Y-%m-%dT%H:%M:%S.00Z"
            ),
            episode.watchedAt,
        )

    def test_addEntry_tvshow_regex4(self):
        entryTitle = "American Horror Story: Murder House: Nachgeburt"
        entryDate = datetime.now()
        self.history.addEntry(entryTitle, entryDate.strftime("%d.%m.%y"))

        show = self.history.getTvShow("American Horror Story")
        self.assertIsNotNone(show)

        season = show.getSeasonByName("Murder House")
        self.assertIsNotNone(season)

        episode = season.getEpisodeByName("Nachgeburt")
        self.assertIsNotNone(episode)
        self.assertIn(
            entryDate.replace(hour=20, minute=15, second=0).strftime(
                "%Y-%m-%dT%H:%M:%S.00Z"
            ),
            episode.watchedAt,
        )

    def test_addEntry_tvshow_regex5(self):
        entryTitle = "King Arthur: Legend of the Sword"
        entryDate = datetime.now()
        self.history.addEntry(entryTitle, entryDate.strftime("%d.%m.%y"))

        movie = self.history.getMovie("King Arthur: Legend of the Sword")
        self.assertIsNotNone(movie)
        self.assertIn(
            entryDate.replace(hour=20, minute=15, second=0).strftime(
                "%Y-%m-%dT%H:%M:%S.00Z"
            ),
            movie.watchedAt,
        )

    def test_addEntry_tvshow_regex6(self):
        entryTitle = "The Mandalorian: Chapter 9"
        entryDate = datetime.now()
        self.history.addEntry(entryTitle, entryDate.strftime("%d.%m.%y"))

        show = self.history.getTvShow("The Mandalorian")
        self.assertIsNotNone(show)

        season = show.getSeasonByNumber(1)
        self.assertIsNotNone(season)

        episode = season.getEpisodeByName("Chapter 9")
        self.assertIsNotNone(episode)
        self.assertIn(
            entryDate.replace(hour=20, minute=15, second=0).strftime(
                "%Y-%m-%dT%H:%M:%S.00Z"
            ),
            episode.watchedAt,
        )

    def test_addEntry_tvshow_regex_invalid(self):
        entryTitle = "Invalid show format"
        entryDate = datetime.now()
        self.history.addEntry(entryTitle, entryDate.strftime("%d.%m.%y"))

        # nothing should have been added
        self.assertEqual(len(self.history.shows), 0)
        self.assertEqual(len(self.history.movies), 1)  # a movie can have any name


class TestNetflixTvShow(unittest.TestCase):
    def setUp(self):
        self.show = NetflixTvShow("Stranger Things")

    def test_addSeason(self):
        season1 = self.show.addSeason(1, "The Vanishing of Will Byers")
        season2 = self.show.addSeason(2, "The Mind Flayer")

        self.assertEqual(len(self.show.seasons), 2)
        self.assertIn(season1, self.show.seasons)
        self.assertIn(season2, self.show.seasons)

    def test_getSeasonByNumber(self):
        season1 = self.show.addSeason(1, "The Vanishing of Will Byers")
        season2 = self.show.addSeason(2, "The Mind Flayer")

        self.assertEqual(self.show.getSeasonByNumber(1), season1)
        self.assertEqual(self.show.getSeasonByNumber(2), season2)
        self.assertIsNone(self.show.getSeasonByNumber(3))

    def test_getSeasonByName(self):
        season1 = self.show.addSeason(1, "The Vanishing of Will Byers")
        season2 = self.show.addSeason(2, "The Mind Flayer")

        self.assertEqual(
            self.show.getSeasonByName("The Vanishing of Will Byers"), season1
        )
        self.assertEqual(self.show.getSeasonByName("The Mind Flayer"), season2)
        self.assertIsNone(self.show.getSeasonByName("The Upside Down"))
