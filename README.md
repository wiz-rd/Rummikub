# Rummikub
This is a simple, digital rendition of the popular board game.

## Why

A good friend of mine and I sometimes play Rummikub when we spend time together but unfortunately, she recently moved far away. I couldn't find any online or other digital versions of Rummikub, so I decided I might as well build one myself so I can enjoy Rummikub with her and our friends again.

This is __NOT__ meant to be a stand-in for the actual game. This is meant just for my friends and I to play a game together while we cannot in person. If there are any legal concerns, please reach out to me and I'll do my best to get them sorted.

## Technologies

So far, this uses:
- SQLite for the database
- Python for the API and web server, and
- I plan to use Godot, exported to the web, for the actual _game_ part of the website.

## How

As this is a webserver and client in the same repository, there isn't a really clean or easy way of setting this up. For now, the steps are as follows:

- Clone the repository
- Navigate into the repository folder
- Setup a Python virtual environment
- Activate it and run `pip install litestar[cryptography]`
- Run `uvicorn server:app`

This should run the server on port 8000. I'll update this with further steps and information but for the time being, what this does is: create a session for you whenever you navigate to the server (e.g. `localhost:8000/api/user/`), store username changes (`localhost:8000/api/user/{username}`), create games (`localhost:8000/api/game/`) and add them to the database,
and join games (`localhost:8000/api/game/{game_id}/join/`) and adds your participation in the game to a table. You can also list the nicknames of players in a game by GET requesting `localhost:8000/api/game/{game_id}/players/`).

Database data and sessions will be stored in the created folders of `./data/` and `./data/sessions/`, respectively.
