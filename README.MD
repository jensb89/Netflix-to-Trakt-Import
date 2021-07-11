# Netflix To Trakt Import

This script imports all watched Netflix tv shows and movies to trakt.tv.

It uses TMDB to find the episode number and id of the show/movie by comparing the 
episode titles / movie names with the ones from the Netflix export file.

By using TMDB multi-language support is provided!

### Specifics:
For each entry, the season number and show name is extracted.
With this information the season is queried from TMDB. 
If the episode name from the Netflix Export matches the episode name from the TMDB season, the Id is filled in.

Otherwise, it is checked if the episode number might be already in the title of the episode.
As a last test, it is checked if the number of episodes in the season equals the number of watched episodes. If this is the case, 
the script will estimate the episode number based on the viewing history (latest watched episode = last episode of the season.)

If no match was found at all, the episode / movie is left out.

## Requirements:
* Trakt.tv account and API Key
* TMDB account and API Key
* Netflix Account
* Python (tested with python 3.8.5 under macOS)

## Installation
Just clone this repo, fill in the API keys and language information in the config.py file.
See how to register API access below.

Install the requirements (trakt.tv and tmdb) by calling:
```bash
python -m pip install -r requirements.txt
```

Also, of course a NetflixViewingHistory.csv export file is needed. This can be obtained directly from the netflix page.
Compare https://help.netflix.com/node/101917 for more information.

To use the script simply call 
```bash
python netflix2trakt.py
```

For printing only the non-found shows just execute
```bash
grep "No Tmdb ID found" Netflix2TraktImportLog.log 
```

### Register API Access at Trakt
* Go to "Settings" under your profile
* Select "Your API Applications"
* Select "New Application"
* Provide a name into "Name" e.g John Smith Import from TV Time
* Paste "urn:ietf:wg:oauth:2.0:oob" into "Redirect uri:"
* Click "Save App"
* Make note of your details to be used later.

## Future improvements:
* Send multiple episodes to trakt in one call instead of making one API call per entry 
* Check found TMDB shows/movies before sending to trakt.tv
* Better print outputs
* Code documentation improvement
* Use only trakt Search and make TMDB optional

I did this on one weekened, so there is probably room for improvement :)