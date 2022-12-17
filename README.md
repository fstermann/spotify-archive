# spotify-archive

![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)
![Linters](https://github.com/fstermann/spotify-archive/actions/workflows/lint.yml/badge.svg)

Archive any spotify playlist using github actions.

Based on [discoverd-weekly](https://github.com/EthanRosenthal/discovered-weekly) by Ethan Rosenthal.

## Idea

Spotify generates new playlists every week, some it updates daily. While it adds new tracks to the playlist,
it does remove the old ones after some time.


But what if you want to keep those tracks forever?


This project uses github actions to archive any playlist you want. It will archive all the newly added tracks into
a specified 'all-time' playlist. Basically, it will copy all the tracks from the daily/weekly playlist to the 'all-time'
and keep your tracks there, so you can come back and listen to them whenever you want.

### Features

In addition to that, it will also check for duplicates, and makes sure that the 'all-time' playlist only contains
unique tracks.


You can also specify an amount of recommendations you want to add to the 'all-time' playlist. These will be generated
based on the recently added tracks of the 'all-time' playlist, as well as the genres specified in the config file.


## Run

Manually run the weekly archive

````bash
$ spotify-archive weekly
````

or the daily one

````bash
$ spotify-archive daily
````

It is recommended though to set up github actions to run the archive.

## Configuration

Add playlists to the `config.yaml` file to include more playlists.
