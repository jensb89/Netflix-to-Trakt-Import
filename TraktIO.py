from __future__ import absolute_import, division, print_function

import json
import logging
import os.path
from threading import Condition
import requests
from trakt import Trakt
import config

# Set up logging based on config
logging.basicConfig(level=config.LOG_LEVEL)


class TraktIO(object):
    # Handles Trakt authorization, caching, and sync logic
    def __init__(self, page_size=50, dry_run=False):
        # Configure Trakt client credentials
        Trakt.configuration.defaults.client(  # pyright: ignore[reportAttributeAccessIssue]
            id=config.TRAKT_API_CLIENT_ID, secret=config.TRAKT_API_CLIENT_SECRET
        )

        self.authorization = None
        self._watched_episodes = set()
        self._watched_movies = set()
        self.cached_watched_episodes = set()
        self._episodes = []
        self._movies = []
        self.dry_run = dry_run
        self.is_authenticating = Condition()
        self.page_size = page_size

        self._initialize_auth()

    # Initialize and load authentication data from file or trigger auth flow
    def _initialize_auth(self):
        if not os.path.isfile("traktAuth.json"):
            self.authenticate()

        if os.path.isfile("traktAuth.json"):
            with open("traktAuth.json") as infile:
                self.authorization = json.load(infile)

            if not self.checkAuthenticationValid():
                print("Authorization is expired, attempting manual refresh...")
                self._refresh_token()

            if self.getWatchedShows() is not None:
                print("Authorization appears valid. Watched shows retrieved.")
                self.cacheWatchedHistory()
            else:
                print(
                    "No watched shows found. Token may still be invalid or no data available."
                )

    # Refresh expired Trakt token manually
    def _refresh_token(self):
        if not self.authorization:
            print("Cannot refresh token, no authorization found.")
            return

        response = requests.post(
            "https://api.trakt.tv/oauth/token",
            json={
                "refresh_token": self.authorization.get("refresh_token"),
                "client_id": config.TRAKT_API_CLIENT_ID,
                "client_secret": config.TRAKT_API_CLIENT_SECRET,
                "redirect_uri": config.TRAKT_REDIRECT_URI,
                "grant_type": "refresh_token",
            },
        )

        if response.status_code == 200:
            self.authorization = response.json()
            with open("traktAuth.json", "w") as outfile:
                json.dump(self.authorization, outfile)
            print("Token successfully refreshed manually.")
        else:
            print("Manual token refresh failed: %s" % response.text)

    # Return authorization headers for Trakt API
    def _get_auth_headers(self):
        if not self.authorization:
            raise Exception("User is not authenticated.")

        return {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": config.TRAKT_API_CLIENT_ID,
            "Authorization": f"Bearer {self.authorization['access_token']}",
        }

    # Check if token is still valid
    def checkAuthenticationValid(self) -> bool:
        if not self.authorization:
            return False
        return "access_token" in self.authorization

    # Fetch watched shows list from Trakt
    def getWatchedShows(self):
        try:
            headers = self._get_auth_headers()
            response = requests.get(
                "https://api.trakt.tv/sync/watched/shows", headers=headers
            )
            if response.status_code == 200:
                json_response = response.json()
                logging.debug(
                    "Trakt watched shows response: %s",
                    json.dumps(json_response, indent=2),
                )
                return json_response
            return None
        except Exception as e:
            print(f"❌ Failed to fetch watched shows: {e}")
            return None

    # Cache watched episodes and movies to avoid resubmitting
    def cacheWatchedHistory(self):
        try:
            logging.info("Fetching watched episodes and movies from Trakt...")
            shows_response = requests.get(
                "https://api.trakt.tv/sync/watched/shows",
                headers=self._get_auth_headers(),
            )
            movies_response = requests.get(
                "https://api.trakt.tv/sync/watched/movies",
                headers=self._get_auth_headers(),
            )

            if shows_response.status_code == 200:
                for show in shows_response.json():
                    for season in show.get("seasons", []):
                        for episode in season.get("episodes", []):
                            self._watched_episodes.add(
                                episode.get("ids", {}).get("trakt")
                            )

            if movies_response.status_code == 200:
                for movie in movies_response.json():
                    tmdb_id = movie.get("movie", {}).get("ids", {}).get("tmdb")
                    if tmdb_id:
                        self._watched_movies.add(tmdb_id)
        except Exception as e:
            logging.error(f"⚠ Error caching Trakt history: {e}")

    # Check if movie was already watched
    def isWatchedMovie(self, tmdb_id: int) -> bool:
        result = tmdb_id in self._watched_movies
        logging.debug(f"isWatchedMovie({tmdb_id}) -> {result}")
        return result

    # Get locally stored movie and episode data for sync
    def getData(self) -> dict:
        return {"movies": self._movies, "episodes": self._episodes}

    # Perform sync to Trakt or dry-run simulation
    def sync(self):
        if self.dry_run:
            logging.info("Dry run enabled. Skipping actual Trakt sync.")
            return {
                "added": {"movies": len(self._movies), "episodes": len(self._episodes)},
                "not_found": {"movies": [], "episodes": [], "shows": []},
                "updated": {"movies": [], "episodes": []},
            }

        headers = self._get_auth_headers()
        payload = json.dumps(self.getData())

        response = requests.post(
            "https://api.trakt.tv/sync/history", headers=headers, data=payload
        )
        if response.status_code != 201:
            raise Exception(
                f"Trakt sync failed: {response.status_code} - {response.text}"
            )

        json_response = response.json()
        logging.debug("Trakt sync response: %s", json.dumps(json_response, indent=2))

        # Sanitize fields to ensure response is safe to iterate over
        for key in ["added", "updated", "not_found"]:
            for subkey in ["movies", "episodes", "shows"]:
                if key in json_response and subkey in json_response[key]:
                    val = json_response[key][subkey]
                    if not isinstance(val, (list, dict)):
                        json_response[key][subkey] = []

        return json_response

    # Handle device authentication flow
    def authenticate(self):
        if not self.is_authenticating.acquire(blocking=False):
            print("Authentication has already been started")
            return False

        code_info = Trakt["oauth/device"].code()  # pyright: ignore[reportAttributeAccessIssue, reportInvalidTypeArguments]

        print(
            '🔑 Enter the code "%s" at %s to authenticate your Trakt account'
            % (code_info.get("user_code"), code_info.get("verification_url"))
        )

        poller = (
            Trakt["oauth/device"]  # pyright: ignore[reportAttributeAccessIssue, reportInvalidTypeArguments]
            .poll(**code_info)  # pyright: ignore[reportAttributeAccessIssue]
            .on("aborted", self.on_aborted)
            .on("authenticated", self.on_authenticated)
            .on("expired", self.on_expired)
            .on("poll", self.on_poll)
        )

        poller.start(daemon=False)
        return self.is_authenticating.wait()

    # Called when user aborts Trakt auth
    def on_aborted(self):
        print("Authentication aborted")
        self._notify_auth_complete()

    # Called when user completes authentication successfully
    def on_authenticated(self, authorization):
        self.authorization = authorization
        print("✅ Authentication successful!")
        with open("traktAuth.json", "w") as f:
            json.dump(self.authorization, f)
        self._notify_auth_complete()

    # Called when auth times out or expires
    def on_expired(self):
        print("Authentication expired")
        self._notify_auth_complete()

    # Called on every poll attempt during auth
    def on_poll(self, callback):
        callback(True)

    # Notify any threads waiting on authentication that it is complete
    def _notify_auth_complete(self):
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()
