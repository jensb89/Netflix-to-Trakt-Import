from __future__ import absolute_import, division, print_function

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
        Trakt.base_url = "http://api.trakt.tv"

        Trakt.configuration.defaults.client(
            id=config.TRAKT_API_CLIENT_ID, secret=config.TRAKT_API_CLIENT_SECRET
        )

        if not (os.path.isfile("traktAuth.json")) and not self.authorization:
            self.authenticate()
        elif os.path.isfile("traktAuth.json"):
            with open("traktAuth.json") as infile:
                self.authorization = json.load(infile)

    def addEpisodeToHistory(self, data):
        self._episodes.append(data)
        if len(self._episodes) >= self.page_size:
            self.sync()

    def addMovie(self, data):
        self._movies.append(data)
        if len(self._movies) >= self.page_size:
            self.sync()

    def getData(self):
        data = {
            "movies": self._movies,
            "episodes": self._episodes
        }
        return data

    def resetData(self):
        self._episodes = []
        self._movies = []

    def sync(self):
        """Submit watch history to Trakt"""
        watchHistory = self.getData()
        if self.dry_run:
            print("** Skipping Trakt sync **")
            logging.debug(watchHistory)
            res = {
                "added": {
                    "movies": len(watchHistory["movies"]),
                    "episodes": len(watchHistory["episodes"]),
                }
            }
        else:
            with Trakt.configuration.oauth.from_response(self.authorization):
                res = Trakt["sync/history"].add(watchHistory)
        print("* %d episodes and %d movies added to Trakt history" % (res["added"]["episodes"], res["added"]["movies"]))
        logging.info(res)
        self.resetData()
        return res

    def authenticate(self):
        if not self.is_authenticating.acquire(blocking=False):
            print("Authentication has already been started")
            return False

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
        return self.is_authenticating.wait()

    def on_aborted(self):
        """Device authentication aborted.
        Triggered when device authentication was aborted (either with `DeviceOAuthPoller.stop()`
        or via the "poll" event)
        """

        print("Authentication aborted")

        # Authentication aborted
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_authenticated(self, authorization):
        """Device authenticated.
        :param authorization: Authentication token details
        :type authorization: dict
        """

        # Acquire condition
        self.is_authenticating.acquire()

        # Store authorization for future calls
        self.authorization = authorization

        print("Authentication successful - authorization: %r" % self.authorization)

        with open("traktAuth.json", "w") as f:
            json.dump(self.authorization, f)

        # Authentication complete
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_expired(self):
        """Device authentication expired."""

        print("Authentication expired")

        # Authentication expired
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

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


# t = TraktIO()
# t.init()
