# Netflix To Trakt Import

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-310/)
![GitHub Issues](https://img.shields.io/github/issues/jensb89/Netflix-to-Trakt-Import)
![GitHub](https://img.shields.io/github/license/jensb89/Netflix-to-Trakt-Import)
[![Python application](https://github.com/jensb89/Netflix-to-Trakt-Import/actions/workflows/python-app.yml/badge.svg)](https://github.com/jensb89/Netflix-to-Trakt-Import/actions/workflows/python-app.yml)
[![Coverage Status](https://coveralls.io/repos/github/jensb89/Netflix-to-Trakt-Import/badge.svg?branch=master)](https://coveralls.io/github/jensb89/Netflix-to-Trakt-Import?branch=master)

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
If your Netflix csv file uses a different datetime format (default: day.month.year) then change the
`viewing_history_datetime_format` setting in the [`config.ini` file](README.MD#configuration).
Note: Use %Y for years like 2023 and %y for year entries like 23. 
If your csv file uses a different delimiter than `,` between date and entry, then change the
`viewing_history_delimiter` option as well.

See how to register API access below.

Install the requirements (trakt.tv and tmdb) by calling:
```bash
python -m pip install -r requirements.txt
```

Also, of course a NetflixViewingHistory.csv export file is needed. This can be obtained directly from the netflix page.
Compare https://help.netflix.com/node/101917 for more information.

Note: There is currently no check if the data is already uploaded. This means, if you use the script more than once, make
sure to delete all previously synced episodes/movies from the csv file.

To use the script simply call 
```bash
python netflix2trakt.py
```

For printing only the non-found shows just execute
```bash
grep "No Tmdb ID found" Netflix2TraktImportLog.log 
```

If execution fails with error _tmdbv3api.exceptions.TMDbException: ['query must be provided']_, set the `strict` option of the
`TMDB` section in [`config.ini` file](README.MD#configuration) to **False**.

If you get an error like: _strptime raise ValueError("time data %r does not match format %r"...) or any other related to the dates in the `NetflixViewingHistory.csv`
Then run the file `history-dates-fixer.py` to get all dates standardized in the required format.

## Configuration

To customize the import options, copy [`config_default.ini`](config_default.ini)
to `config.ini` and make your changes there.

```bash
cp config_default.ini config.ini
# open config.ini in the editor of your choice
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
* Check found TMDB shows/movies before sending to trakt.tv
* Better print outputs
* Use only trakt Search and make TMDB optional

I did this on one weekened, so there is probably room for improvement :)
