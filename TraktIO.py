from __future__ import absolute_import, division, print_function

from trakt import Trakt

from threading import Condition
import logging
import os.path
import config 

import json


logging.basicConfig(level=logging.DEBUG)


class TraktIO(object):
    def __init__(self):
        self.is_authenticating = Condition()

        self.authorization = None

        # Bind trakt events
        Trakt.on('oauth.token_refreshed', self.on_token_refreshed)
    
    def init(self):
        Trakt.base_url = 'http://api.trakt.tv'

        Trakt.configuration.defaults.client(
            id=config.TRAKT_API_CLIENT_ID,
            secret=config.TRAKT_API_CLIENT_SECRET
        )

        if not(os.path.isfile("traktAuth.json")) and not self.authorization:
            self.authenticate()
        elif os.path.isfile("traktAuth.json"):
            with open('traktAuth.json') as infile:
                self.authorization = json.load(infile)

    def addEpisodeToHistory(self, data):
        with Trakt.configuration.oauth.from_response(self.authorization):
            Trakt["sync/history"].add(data)
    
    def addMovie(self, data):
        with Trakt.configuration.oauth.from_response(self.authorization):
            Trakt["sync/history"].add(data)

    def authenticate(self):
        if not self.is_authenticating.acquire(blocking=False):
            print('Authentication has already been started')
            return False

        # Request new device code
        code = Trakt['oauth/device'].code()

        print('Enter the code "%s" at %s to authenticate your account' % (
            code.get('user_code'),
            code.get('verification_url')
        ))

        # Construct device authentication poller
        poller = Trakt['oauth/device'].poll(**code)\
            .on('aborted', self.on_aborted)\
            .on('authenticated', self.on_authenticated)\
            .on('expired', self.on_expired)\
            .on('poll', self.on_poll)

        # Start polling for authentication token
        poller.start(daemon=False)

        # Wait for authentication to complete
        return self.is_authenticating.wait()

    def on_aborted(self):
        """Device authentication aborted.
        Triggered when device authentication was aborted (either with `DeviceOAuthPoller.stop()`
        or via the "poll" event)
        """

        print('Authentication aborted')

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

        print('Authentication successful - authorization: %r' % self.authorization)

        with open('traktAuth.json', 'w') as f:
            json.dump(self.authorization, f)

        # Authentication complete
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_expired(self):
        """Device authentication expired."""

        print('Authentication expired')

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

        print('Token refreshed - authorization: %r' % self.authorization)

#t = TraktIO()
#t.init()