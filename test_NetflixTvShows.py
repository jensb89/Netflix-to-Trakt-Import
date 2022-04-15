from NetflixTvShow import NetflixTvHistory


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
    assert netflixHistory.shows[0].seasons[0].episodes[0].watchedAt[0] == "03.10.21"


def test_addMultipleTvShows():
    """Test tp add 3 episodes of 2 different shows and check that both shows and number of episodes are correct"""
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
    assert netflixHistory.hasTvShow("Peaky Blinders – Gangs of Birmingham")
    assert netflixHistory.hasTvShow("Haus des Geldes")
    assert (
        len(netflixHistory.getTvShow("Haus des Geldes").getSeasonByNumber("5").episodes)
        == 2
    )


def test_addMovie():
    """Test to add a movie and check if it was recoginzied as a movie"""
    netflixHistory = NetflixTvHistory()
    netflixHistory.addEntry("Spider-Man: Far from Home", "16.09.21")
    assert netflixHistory.getMovie("Spider-Man: Far from Home") is not None
    assert netflixHistory.movies[0].watchedAt[0] == "16.09.21"
