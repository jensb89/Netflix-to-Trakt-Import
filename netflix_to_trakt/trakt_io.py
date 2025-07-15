from __future__ import absolute_import, division, print_function

import datetime
import json
import logging
import os.path
from threading import Condition

from trakt import Trakt

import config

logging.basicConfig(level=config.LOG_LEVEL)


class TraktIO(object):
    def __init__(self, page_size=1000, dry_run=False):
        self.authorization = None
        self.dry_run = dry_run
        self.is_authenticating = Condition()
        self.page_size = page_size

        self.resetData()

        # Bind trakt events
        Trakt.on("oauth.token_refreshed", self.on_token_refreshed)

    def init(self):
        Trakt.base_url = "https://api.trakt.tv"

        Trakt.configuration.defaults.client(
            id=config.TRAKT_API_CLIENT_ID, secret=config.TRAKT_API_CLIENT_SECRET
        )

        if not (os.path.isfile("traktAuth.json")) and not self.authorization:
            self.authenticate()
        elif os.path.isfile("traktAuth.json"):
            with open("traktAuth.json") as infile:
                self.authorization = json.load(infile)
            if not (self.checkAuthenticationValid()):
                print("Authorization is expired, a refresh is tried:")
                if self.getWatchedShows() is None:
                    print(
                        "No watched shows found, authorization might have not worked or no shows have been watched. For the first case try to remove the 'traktAuth.json' file!"
                    )
                else:
                    print("Wathced shows could be retrieved, authorization is working.")

    def getWatchedShows(self):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            watched = Trakt["sync/watched"].shows()
            return watched

    def checkAuthenticationValid(self) -> bool:
        created = self.authorization.get("created_at")
        expired = self.authorization.get("expires_in")
        return int(datetime.datetime.now().timestamp()) < created + expired

    def addEpisodeToHistory(self, data):
        self._episodes.append(data)
        if len(self._episodes) >= self.page_size:
            self.sync()

    def addMovie(self, data):
        self._movies.append(data)
        if len(self._movies) >= self.page_size:
            self.sync()

    def getData(self):
        data = {"movies": self._movies, "episodes": self._episodes}
        return data

    def resetData(self):
        self._episodes = []
        self._movies = []

    def sync(self):
        """Submit watch history to Trakt"""
        watchHistory = self.getData()
        res = None
        if self.dry_run:
            print("** Skipping Trakt sync **")
            logging.debug(watchHistory)
            res = {
                "added": {
                    "movies": len(watchHistory["movies"]),
                    "episodes": len(watchHistory["episodes"]),
                }
            }
            print(res)

        else:
            # no refresh here, because we refresh already at init
            with Trakt.configuration.oauth.from_response(self.authorization):
                res = Trakt["sync/history"].add(watchHistory)
                output = "* %d episodes and %d movies added to Trakt history" % (
                    res["added"]["episodes"],
                    res["added"]["movies"],
                )
                logging.info(output)

        if res is None:
            logging.error(
                "Something went wrong, Trakt sync failed! May delete the traktAuth.json file to reconnect to your Trakt account."
            )
            self.resetData()
            return res

        logging.info(res)
        self.resetData()

        return res

    def authenticate(self):

        #acquire() was called non-blocking
        # if not self.is_authenticating.acquire(blocking=False):
        #    print("Authentication has already been started")
        #    return False

        with self.is_authenticating:
        if getattr(self, '_auth_in_progress', False):
            print("Authentication has already been started")
            return False

        self._auth_in_progress = True

        # Request new device code
        code = Trakt["oauth/device"].code()
        print(
            'Enter the code "%s" at %s to authenticate your account'
            % (code.get("user_code"), code.get("verification_url"))
        )

        # Construct device authentication poller
        poller = (
            Trakt["oauth/device"]
            .poll(**code)
            .on("aborted", self.on_aborted)
            .on("authenticated", self.on_authenticated)
            .on("expired", self.on_expired)
            .on("poll", self.on_poll)
        )

        # Start polling for authentication token
        poller.start(daemon=False)

        # Wait for authentication to complete
        # Condition.wait() expects the lock to be acquired first
        self.is_authenticating.wait()

    def on_aborted(self):
        """Device authentication aborted.
        Triggered when device authentication was aborted (either with `DeviceOAuthPoller.stop()`
        or via the "poll" event)
        """

        with self.is_authenticating:
            logging.warning("Authentication aborted by user or system.")

        self._auth_in_progress = False
        self.is_authenticating.notify_all()

    def on_authenticated(self, authorization):
        """Device authenticated.
        :param authorization: Authentication token details
        :type authorization: dict
        """

        with self.is_authenticating:
            self.authorization = authorization

        # Save the token for future use
        with open("traktAuth.json", "w") as f:
            json.dump(self.authorization, f)

        logging.info("Authentication successful: %r", self.authorization)

        self._auth_in_progress = False
        self.is_authenticating.notify_all()

    def on_expired(self):
        """Device authentication expired."""
        # Authentication expired
        with self.is_authenticating:
        logging.warning("Authentication expired. Please try again.")

        self._auth_in_progress = False
        self.is_authenticating.notify_all()

    def on_poll(self, callback):
        """Device authentication poll.
        :param callback: Call with `True` to continue polling, or `False` to abort polling
        :type callback: func
        """

        # Continue polling
        callback(True)

    def on_token_refreshed(self, authorization):
        # OAuth token refreshed, store authorization for future calls
        self.authorization = authorization

        print("Token refreshed - authorization: %r" % self.authorization)

        with open("traktAuth.json", "w") as f:
        json.dump(self.authorization, f)


# t = TraktIO()
# t.init()
