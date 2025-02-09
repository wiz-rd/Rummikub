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
import asyncio
import sqlite3
from pathlib import Path
from json import JSONDecodeError

# broad litestar imports
from litestar.logging import LoggingConfig
from litestar import Litestar, status_codes
from litestar.config.cors import CORSConfig
from litestar.exceptions import HTTPException
from litestar.middleware.session.base import ONE_DAY_IN_SECONDS

# requests and responses
from litestar.connection import Request
from litestar.response.sse import ServerSentEventMessage, ServerSentEvent

# handling clients and sessions
from litestar.stores.file import FileStore
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig, ServerSideSessionBackend

# controllers and routes
from litestar.router import Router
from litestar.controller import Controller
from litestar.handlers import get, post, put

# custom imports
from functions import *

"""
NOTE: make sure to close each connection after it's
served its purpose. This should hopefully save on resources.
"""

###################
# CONST VARIABLES #
###################

# a set of the queues for each game
# NOTE: IMPLEMENT something to remove
# a game from this set if it's been
# ended or deleted in some way
queues = {}

UNAUTHORIZED_RESPONSE = {
    "status_code": status_codes.HTTP_401_UNAUTHORIZED,
    "detail": "User is not authorized."
}

DATA_FOLDER = os.path.normpath(os.path.abspath("./data"))
DATA_DB = os.path.join(DATA_FOLDER, "data.db")
SESSION_FOLDER = os.path.join(DATA_FOLDER, "sessions")
# create all folders if they don't exist already.
os.makedirs(SESSION_FOLDER, exist_ok=True)

SESSION_CONFIG = ServerSideSessionConfig(
    renew_on_access=True,
    # half a day for them to keep their session alive
    max_age=ONE_DAY_IN_SECONDS / 2,
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


async def authed(authorized: bool) -> None:
    """
    Simple helper method to automatically
    raise an HTTP error if the user isn't authorized.

    I don't know of a better way to change status codes
    as far as Uvicorn is concerned; just returning a
    dictionary with "status_code" as a key doesn't work.
    """
    if not authorized:
        raise HTTPException(
            status_code=UNAUTHORIZED_RESPONSE["status_code"],
            detail=UNAUTHORIZED_RESPONSE["detail"],
        )


async def is_authenticated(req: Request):
    """
    Returns whether or not the user
    has a valid session ID, a simple authentication.

    This, most likely, is completely
    redundant because sessions are created
    automatically if the user doesn't already
    have one, so...

    But I'll leave it for now, both for
    future use and just as an extra precaution.
    """
    # if the client doesn't have a session
    if not req.session:
        return False

    # if the client has a session not on the server side
    # NOTE: this throws an error because it's not awaited,
    # but I really don't know how they expect me to do this
    exists = await SESSION_FILE_STORE.exists(req.get_session_id())

    if exists:
        return True
    else:
        # delete expired in case it's an expired session
        SESSION_FILE_STORE.delete_expired()
        return False


##########################
# ROUTES AND CONTROLLERS #
##########################


########
# GAME #
########


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
        auth = await is_authenticated(request)
        await authed(auth)

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

        # thanks Python for not letting me put
        # awaits in if statements
        auth = await is_authenticated(request)
        await authed(auth)

        data, columns = get_game_data(con, game_id)

        # if no data is found for the game ID,
        # the game does not exist; return a 404
        if data is None:
            raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="There is no game with that ID.")
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


    @get(path="/{game_id:str}/players", status_code=status_codes.HTTP_200_OK)
    async def list_players(self, request: Request, game_id: str) -> list | dict:
        """
        Responds with a list of players in the specified game.
        """
        auth = await is_authenticated(request)
        await authed(auth)

        player_sessions = get_players_in_game(con, game_id)

        if player_sessions is not None and len(player_sessions) >= 1:
            players = list()
            for session in player_sessions:
                # this has multiple steps:
                # 1. get session contents
                # 2. convert from bytes to dict
                # 3. get the username from the dict
                username = await SESSION_BACKEND.get(session, SESSION_FILE_STORE)
                # if there isn't a session anymore,
                # skip this user.
                if username is None:
                    continue

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
        auth = await is_authenticated(request)
        await authed(auth)

        does_not_exist = {
            "status_code": status_codes.HTTP_404_NOT_FOUND,
            "detail": "That game does not exist."
        }

        first_resulting_game = get_game_data(con, game_id)[0]

        if first_resulting_game is None:
            return does_not_exist

        game_exists: bool = len(first_resulting_game) >= 1
        current_game_players = get_players_in_game(con=con, gameID=game_id)

        game_state = run_db_command(
            con=con,
            command=f"SELECT gameState FROM games WHERE gameID == '{game_id}';"
        )

        # if the game doesn't exist, this doesn't really matter
        if len(game_state) < 1:
            game_state = "NONEXISTANT"
        # otherwise, get its state
        else:
            game_state = game_state[0]

        at_max_players = len(current_game_players) >= MAX_POSSIBLE_PLAYERS

        # if the game exists (the database responds with anything)
        # and if the user is NOT in that game currently, let them join.
        # ONLY IF THE GAME IS IN THE PREGAME STATE; other game states
        # such as ONGOING or ENDED shouldn't allow them to join, for obvious reasons
        if not at_max_players and game_exists and (request.get_session_id() not in current_game_players) and (game_state == "PREGAME"):
            await insert_into_table(
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
                "status_code": status_codes.HTTP_200_OK,
                "detail": "Success"
            }
        elif not game_exists:
            return does_not_exist
        else:
            # otherwise, let them know
            return {
                "status_code": status_codes.HTTP_409_CONFLICT,
                "detail": "User is already in game."
            }


    @get("/{game_id:str}/notify")
    async def notify_changes(self, request: Request, game_id: str) -> ServerSentEvent:
        """
        Notifies the client with an SSE when a
        change is made to the game in question,
        that way they can request the new board
        layout from here.

        I was going to send the whole data to the
        client but I think this is better.
        """
        auth = await is_authenticated(request)
        await authed(auth)

        vareaiable = ServerSentEvent(
            content="data",
        )

        return vareaiable

    @get("/{game_id:str}/board")
    async def board_info(self, request: Request, game_id: str) -> dict:
        """
        Returns the board info and user's hand
        if they are authenticated.
        """
        auth = await is_authenticated(request)
        await authed(auth)

        players = get_players_in_game(con, game_id)
        session_id = "97fb41f38dd46b14dd3255589ea3d13329af7251804ce76a8bdde2aa0cb02a3f" # request.get_session_id()


        # TODO UNCOMMENT THIS AUTHENTICATION


        # # NOTE: this returns an AUTH ALSO
        # # spent some time debugging this
        # # if the user isn't in the game, tell them
        # if session_id not in players:
        #     await authed(False)

        # grabbing the game data
        # both game_str and columns should be lists
        game_str, columns = get_game_data(con, game_id)

        # if the game or columns don't exist
        if game_str is None or columns is None:
            raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="There is no game with that ID.")

        game = Game()
        game.construct_from_db(game_str, columns)
        # remove the pool before sending it to the client
        # I *could* make a DTO but I feel like that'd needlessly
        # duplicate all other data; it's not like half of the values
        # are sent to client, it's all data, just without the pool
        # specifically, so I think this is wisest, at least for now
        del game.table.pool

        ingame_row = run_db_command(
            con=con,
            command=f"SELECT * FROM ingame WHERE gameID == '{game_id}' AND userID == '{session_id}';"
        )

        # if user isn't in that game or the
        # game doesn't exist period
        if len(ingame_row) <= 0:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="The game and user pair does not exist."
            )

        hand = Hand()

        # get the first item from the list of ingame rows
        # and then get the last item in the list, the Hand
        hand.construct_from_db(ingame_row[0][3])

        return {
            "status_code": status_codes.HTTP_200_OK,
            "game": game,
            "hand": hand,
        }


########
# USER #
########


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
                "status_code": status_codes.HTTP_200_OK,
                "detail": f"Your username was successfully set to {username}."
            }
        except AttributeError:
            raise HTTPException(status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR, detail="Something went wrong...")

    @get("/")
    async def get_username(self, request: Request) -> dict:
        """
        Responds with the username
        """
        default = {
            "status_code": status_codes.HTTP_418_IM_A_TEAPOT,
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
                "status_code": status_codes.HTTP_200_OK,
                "detail": "You have a username.",
                "username": username,
            }

        # if they don't have a username but DO have a session
        return default


##################
# GENERIC ROUTES #
##################


@get("/")
async def api_base_route() -> dict[str, str]:
    """
    Returns a simple success message indicating the
    API/server is functioning properly.
    """
    return {"status_code": status_codes.HTTP_200_OK, "detail": "The API is up and running."}


@get("/clear")
async def api_clear_sessions() -> None:
    """
    Clears sessions that have expired.

    Also, removes users from games if their sesions have expired.
    """
    await SESSION_FILE_STORE.delete_expired()

    players = run_db_command(
        con=con,
        command="SELECT userID FROM ingame;"
    )

    # get the first item from the list/tuple response
    players = [x[0] for x in players]

    for pl in players:
        if not await SESSION_FILE_STORE.exists(pl):
            run_db_command(
                con=con,
                command=f"DELETE FROM ingame WHERE userID == {pl};"
            )


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
