#!/usr/bin/python3

# created by @wiz-rd

"""
To run this server, run:

uvicorn server:app

This will most likely be different
for a Linux machine.
"""

# default imports
import os
import sqlite3
from pathlib import Path
from json import JSONDecodeError

# broad litestar imports
from litestar.connection import Request
from litestar.logging import LoggingConfig
from litestar.config.cors import CORSConfig
from litestar.exceptions import HTTPException
from litestar import Litestar, MediaType, status_codes

# handling clients and sessions
from litestar.stores.file import FileStore
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig, ServerSideSessionBackend

# controllers and routes
from litestar.router import Router
from litestar.controller import Controller
from litestar.handlers import get, post, delete, put

# custom imports
from functions import *

"""
NOTE: make sure to close each connection after it's
served its purpose. This should hopefully save on resources.
"""

###################
# CONST VARIABLES #
###################

UNAUTHORIZED_RESPONSE = {
    "status_code": 401,
    "detail": "User is not authorized."
}

DATA_FOLDER = os.path.normpath(os.path.abspath("./data"))
DATA_DB = os.path.join(DATA_FOLDER, "data.db")
SESSION_FOLDER = os.path.join(DATA_FOLDER, "sessions")
# create all folders if they don't exist already.
os.makedirs(SESSION_FOLDER, exist_ok=True)

SESSION_CONFIG = ServerSideSessionConfig(
    renew_on_access=True,
    max_age=60 * 30,  # 60 seconds times 30 (minutes)
)

SESSION_BACKEND = ServerSideSessionBackend(SESSION_CONFIG)
SESSION_FILE_STORE = FileStore(path=Path(SESSION_FOLDER))

lgr = LoggingConfig(
    root={"level": "INFO", "handlers": ["queue_listener"]},
    formatters={
        "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
    },
    log_exceptions="always",
)

#############################
# INITIALIZING THE DATABASE #
#############################


con = sqlite3.connect(DATA_DB)
initialize_db_and_tables(con)


###############################
# AUTHENTICATION AND SESSIONS #
###############################


def is_authenticated(req: Request):
    """
    Returns whether or not the user
    has a session ID, a simple authentication.

    This, most likely, is completely
    redundant because sessions are created
    automatically if the user doesn't already
    have one, so...

    But I'll leave it for now, both for
    future use and just as an extra precaution.
    """
    if not req.session:
        return False
    return True


##########################
# ROUTES AND CONTROLLERS #
##########################


class GameController(Controller):
    """
    A simple controller for Games.

    Used to create and get data for Games.
    """
    path = "/game"

    @post()
    async def create_game(self, request: Request) -> Game | dict:
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
        if not is_authenticated(request):
            return UNAUTHORIZED_RESPONSE

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
    async def get_game(self, request: Request, game_id: str) -> Game | dict:
        """
        Returns most information about a game,
        should the user have the right permissions.
        """
        # if the user isn't authenticated,
        # avoid giving them any information
        # to limit the damage of DoS and other
        # types of attacks.
        # TODO: Implement this.
        if not is_authenticated(request):
            return UNAUTHORIZED_RESPONSE

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


    @get(path="/{game_id:str}/players", status_code=200)
    async def list_players(self, request: Request, game_id: str) -> list | dict:
        """
        Responds with a list of players in the specified game.
        """
        if not is_authenticated(request):
            return UNAUTHORIZED_RESPONSE

        player_sessions = get_players_in_game(con, game_id)

        if player_sessions:
            players = list()
            for session in player_sessions:
                # this has multiple steps:
                # 1. get session contents
                # 2. convert from bytes to dict
                # 3. get the username from the dict
                username = await SESSION_BACKEND.get(session, SESSION_FILE_STORE)
                try:
                    username = json.loads(username)["username"]
                except KeyError:
                    # if there somehow isn't a username,
                    # just skip them
                    # NOTE: keep an eye on this.
                    continue
                players.append(username)
            return players
        else:
            return []

    # NOTE: Should I have /join/?
    # most likely, yes, to be distinct
    # from patch requests for where
    # someone is making a move in game.
    @post(path="/{game_id:str}/join")
    async def join_game(self, request: Request, game_id: str) -> dict:
        """
        Attempts to let a player join a game.
        """
        if not is_authenticated(request):
            return UNAUTHORIZED_RESPONSE

        does_not_exist = {
            "status_code": 404,
            "detail": "That game does not exist."
        }

        if get_game_data(con, game_id)[0] is None:
            return does_not_exist

        game_exists: bool = len(get_game_data(con, game_id)[0]) >= 1

        current_game_players = get_players_in_game(
            con=con,
            gameID=game_id
        )

        # if the game exists (the database responds with anything)
        # and if the user is NOT in that game currently, let them join.
        if game_exists and request.get_session_id() not in current_game_players:
            insert_into_table(
                con,
                "ingame",
                [
                    # "userID" in the ER diagram
                    request.get_session_id(),
                    game_id,
                    # this (turnNumber) actually doesn't matter right now
                    0,
                    Hand()
                ]
            )
            return {
                "status_code": 200,
                "detail": "Success"
            }
        elif not game_exists:
            return does_not_exist
        else:
            # otherwise, let them know
            return {
                "status_code": 409,
                "detail": "User is already in game."
            }


class UserController(Controller):
    """
    A simple controller for users
    to create and get their own data
    based on sessions.
    """
    path = "/user"

    # so this is a put becuase
    # the value being changed isn't
    # really a "whole object"
    # AND it's 'idempotent,' meaning
    # no matter how many times you send
    # PUT /api/user/gamer, it'll always
    # result in just "gamer" being your username
    @put("/{username:str}")
    async def set_username(self, request: Request, username: str) -> dict:
        try:
            session = request.session
            session["username"] = username
            return {
                "status_code": 200,
                "detail": f"Your username was successfully set to {username}."
            }
        except AttributeError:
            raise HTTPException(status_code=500, detail="Something went wrong...")

    @get("/")
    async def get_username(self, request: Request) -> dict:
        """
        Responds with the username
        """
        default =  {
            "status_code": 418,
            "detail": "You do not have a username.",
            "username": "",
        }

        try:
            session = request.session
        except AttributeError:
            # if they don't have a session
            return default
        # try and grab their username
        username = session.get("username", None)
        if username:
            return {
                "status_code": 200,
                "detail": "You have a username.",
                "username": username,
            }

        # if they don't have a username but DO have a session
        return default


@get("/")
async def api_base_route() -> dict[str, str]:
    """
    Returns a simple success message indicating the
    API/server is functioning properly.
    """
    return {"status_code": 200, "detail": "The API is up and running."}


@get("/clear")
async def api_clear_sessions() -> None:
    """
    Clears sessions that have expired.
    """
    await SESSION_FILE_STORE.delete_expired()
    return

################
# SERVER SETUP #
################

URL = "http://localhost/"
cors_config = CORSConfig(allow_origins=[URL])
rate_limit = RateLimitConfig(rate_limit=("second", 30))

api_base = Router(path="/api", route_handlers=[api_base_route,api_clear_sessions,GameController,UserController])

app = Litestar(
    route_handlers=[api_base],
    stores={"sessions": SESSION_FILE_STORE},
    middleware=[rate_limit.middleware, SESSION_CONFIG.middleware],
    logging_config=lgr,
    # cors_config=cors_config,
)
