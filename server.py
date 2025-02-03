#!/usr/bin/python3

# created by @wiz-rd

"""
To run this server, run:

uvicorn server:app

This will most likely be different
for a Linux machine.
"""

# default imports
import sqlite3
from uuid import UUID
from json import JSONDecodeError

# generic starlite imports
from starlite import Starlite, HTTPException, MediaType, status_codes, CORSConfig, CSRFConfig
from starlite.middleware import RateLimitConfig

# controllers and routes
from starlite.types import Partial
from starlite.router import Router
from starlite.controller import Controller
from starlite.handlers import get, post, patch, delete

# custom imports
from functions import *

"""
NOTE: make sure to close each connection after it's
served its purpose. This should hopefully save on resources.
"""

#############################
# INITIALIZING THE DATABASE #
#############################

con = sqlite3.connect(DATA_DB)
initialize_db_and_tables(con)


# TODO: implement OAuth or something
# similar for users.
def authenticate_player() -> bool:
    """
    Verifies the user is who they
    claim to be.
    """
    return True


##########################
# ROUTES AND CONTROLLERS #
##########################


class GameController(Controller):
    path = "/game"

    @post()
    async def create_game(self) -> Game:
        """
        Creates a game in the database.

        NOTE: This will need to worry
        about proper authority and rate
        limiting once I start to work on that.
        For the time being, this will
        simply create a game when asked to.
        """
        # TODO: make sure this ability
        # to create games at will
        # isn't just open to the internet
        if not authenticate_player():
            return

        # create game here
        game = Game()

        # then, add it to the database
        insert_into_table(
            con=con,
            table_name="games",
            data=game.db_list(),
        )

        # TODO: handle custom settings if the client
        # adds them here? For the time being,
        # I'll just make a default game everytime this
        # url is loaded by a client and will respond
        # with data about the game.
        return game

    @get(path="/{game_id:str}")
    async def get_game(self, game_id: str) -> dict:
        """
        Returns most information about a game,
        should the user have the right permissions.
        """
        # TODO: I don't know how to handle sessions.
        # I should probably use Google OAuth
        # or something similar? I'm really unsure.
        # For the time being, I'll return full data
        # about a game just so I can test the API
        # and database in tandem.
        # Another alternative is Passport.js

        # if the user isn't authenticated,
        # avoid giving them any information
        # to limit the damage of DoS and other
        # types of attacks.
        # TODO: Implement this.
        if not authenticate_player():
            return

        data, columns = get_game_data(con, game_id)

        # if no data is found for the game ID,
        # the game does not exist; return a 404
        if data is None:
            raise HTTPException(status_code=404, detail="There is no game with that ID.")
        elif columns is None:
            logger.critical("Game data received from database is not None but columns returns None.")
            raise HTTPException(status_code=500, detail="There seems to be an issue with the database. Code: game-columns")

        # preparing a dictionary so the
        # data sent to the client is more
        # verbose and easier to parse through
        # instead of just a list
        dictionary = dict()

        for i, cl in enumerate(columns):
            # only converts the item in the list
            # to JSON if it's valid JSON
            # (i.e., not a string such as a UUID or game state)
            try:
                dictionary[cl] = json.loads(data[i])
            except JSONDecodeError:
                dictionary[cl] = data[i]

        # NOTE: DELETES THE POOL
        # the client should not see
        # what tiles remain, so
        # this removes them from the dict
        # before sending it out.
        del dictionary["tableContents"]["pool"]

        return dictionary


    # TODO NOTE: Should I have /join/?
    # this IS a patch request, after all...
    # most likely, yes, to be distinct
    # from patch requests for a game where
    # someone is making a move in game.
    @patch(path="/join/{game_id:str}")
    async def join_game(self, game_id: str) -> dict:
        """
        Attempts to let a player join a game.
        """
        current_game_players = get_players_in_game(
            con=con,
            gameID=game_id
        )

        # TODO: identify player UUID via OAuth

        return current_game_players


@get("/")
async def base_route() -> dict[str, str]:
    """
    Returns a simple success message indicating the
    API/server is functioning properly.
    """
    return {"status_code": 200, "detail": "The API is up and running."}


################
# SERVER SETUP #
################

URL = "http://localhost/"
SECRET = "temporary-secret"
cors_config = CORSConfig(allow_origins=[URL])
csrf_conf = CSRFConfig(secret=SECRET)
rate_limit = RateLimitConfig(rate_limit=("second", 30))

api_base = Router(path="/api", route_handlers=[base_route,GameController])

app = Starlite(
    route_handlers=[api_base],
    # cors_config=cors_config,
    # csrf_config=csrf_conf,
    # middleware=[rate_limit.middleware]
)

app.logger = logger