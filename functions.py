#!/usr/bin/python3

# created by @wiz-rd

"""
This is the first iteration of a game server
that should, at least for now, serve only as
a game API. It should create and store game
and player data. It should NOT serve up a
webpage or something similar, although I
may expand it to fulfill that purpose at a
later date.

Please NOTE: credentials are NOT meant to be
legitimate credentials, and cheating/impersonating
is NOT REGULATED. It's literally just so you can
see your hand and stats on multiple devices. Thus,
I'm not going to make this very secure as far as the
database itself, at least. Its contents will be secured
to the best of my ability, but that's about the best
I can offer.

I'll ask everyone to make sure their passwords are
NOT ones they've used ANYWHERE else, because although
these will be hashed etc to the best of ability,
I have no real idea of industry standards and the like,
and there is basically nothing worth defending with a
crazy password (your stats..?), so that'll be my advice.
"""

import os
import random
import logging
from itertools import chain

from classes import *


DATA_FOLDER = os.path.normpath(os.path.abspath("./data"))
# NOTE: please see above regarding credentials
DATA_DB = os.path.join(DATA_FOLDER, "data.db")
LOGGING_FORMAT = "%(asctime)s \t %(levelname)s \t [%(filename)s] -> %(message)s"
logger = logging.getLogger(__name__)
logging.basicConfig(filename="server.log", level=logging.INFO, format=LOGGING_FORMAT)

"""
This is a brief outline of the database and what
tables and other contents it'll contain.

###########

Users Table:

Emails will NOT be used, and likely won't even be collected to avoid being breached.
It would literally only be a preventative measure for DoS'ing or spamming
the database. Having a hash of them could prevent making multiple accounts
with the same email, hence this field.

###########

Games Table:


NOTE: the game should be able to be entirely reconstructed
from an entry in the Games table, one way or another.

###########

Ingame Table:

(JOIN TABLE)

NOTE: This table stores WHO is in a game and WHAT games they're in.
It's a join table to handle a many-to-many relationship between
players and games.
"""


####################
# INTERNAL METHODS #
####################


def initialize_db_and_tables(con) -> None:
    """
    Creates the database if there isn't one already
    and adds the appropriate tables etc.
    """

    req_tables_and_queries = {
        "games": """CREATE TABLE games(
        gameID TEXT,
        gameState TEXT,
        tableContents TEXT,
        currentPlayerTurn TEXT,
        gameData TEXT,
        PRIMARY KEY(gameID DESC));""",
        # TODO: Should I store current player uuid or position?
        # gameData is things like time
        # for a turn, each player's score,
        # the placement of each player, etc.
        # table should store stuff like
        # the sets and runs on the table
        # and the pool of remaning tiles

        "users": """CREATE TABLE users(
        userID TEXT,
        userName TEXT,
        email TEXT,
        password TEXT,
        wins INTEGER,
        losses INTEGER,
        lastLogon TEXT,
        PRIMARY KEY(userID DESC));""",

        "ingame": """CREATE TABLE ingame(
        gameID INTEGER,
        playerID TEXT,
        hand TEXT,
        turnNumber INT,
        FOREIGN KEY(gameID) REFERENCES games(gameID),
        FOREIGN KEY(playerID) REFERENCES users(userID));""",
    }

    cur = con.cursor()
    tables_res = cur.execute("SELECT name FROM sqlite_master")

    # "flattening" the table using itertools
    # and chain.from_terable. This makes it all
    # into a single list of items
    tables = tables_res.fetchall()
    temp_chain = chain.from_iterable(tables)
    tables = list(temp_chain)

    # NOTE:
    # this will generate a lot of logs if it's ran every time
    # something is performed, which is why this function is
    # intended to be ran only once - when server.py is started
    # up again. it's a sanity check.
    logger.info("Tables in database: %s", tables)

    for tb in req_tables_and_queries:
        # if the table doesn't exist,
        # create it.
        # the tables should absolutely be created
        # after the very first run, hence the warnings later.

        # note that executemany is probably more performant than
        # multiple execute()s but this should only be called once.
        # and have an executemany instead of many manual execute()s.
        if tb not in tables:
            logger.warning(msg=f"Table {tb} does not exist. Creating.")
            cur.execute(req_tables_and_queries[tb])

    con.commit()
    cur.close()


def insert_into_table(con, table_name, data: list | str) -> None:
    """
    This should be called when a user is created,
    for example. Data should be either a string or list
    of items. Examples:

    "'ID', 'username', 'email'..." OR
    ["ID", "username", "email",...]

    A list is probably easier. See the attached ER diagram for
    how to format each specific table.
    """
    cur = con.cursor()

    if isinstance(data, str):
        query = f"INSERT INTO {table_name} VALUES({data});"
    else:
        # put quotes around everything for the query
        data = [f"'{x}'" for x in data]
        query = f"INSERT INTO {table_name} VALUES({', '.join(data)});"

    res = cur.execute(query)
    res.close()
    con.commit()
    logger.debug(f"Added entry to {table_name}.")


# TODO: potentially modify this to have a bit more of
# a universal method like the one below
def get_game_data(con, gameID: int) -> tuple:
    """
    Gets data for the specified game ID.
    Basically pre-generates a nice command for you
    to automatically grab the specified game.
    """
    cur = con.cursor()

    query = f"SELECT * FROM games WHERE gameID == '{gameID}';"

    game_data_res = cur.execute(query)
    game_data = game_data_res.fetchone()
    game_data_res.close()
    cur.close()

    return game_data


def _get_game_or_player(con, ID: str | int) -> list | None:
    """
    A kind of "internal" method that calls similar code
    regarding the join table "ingame". This consolidates the two
    functions into one instead of writing the code twice.

    If a player ID is given, it returns the games they're in.

    If a game ID is given, it returns the players in that game.
    """
    cur = con.cursor()
    
    if isinstance(ID, str):
        query = f"SELECT gameID FROM ingame WHERE playerID == '{ID}';"
    elif isinstance(ID, int):
        query = f"SELECT playerID FROM ingame WHERE gameID == '{ID}';"
    else:
        logger.critical(f"A faulty ID was passed to get a row from INGAME. The id: {ID}. Nothing will be returned.")
        return None

    games_data_res = cur.execute(query)
    games_data = games_data_res.fetchall()
    games_data_res.close()
    cur.close()

    temp_chain = chain.from_iterable(games_data)
    games_data = list(temp_chain)

    return games_data


def get_games_with_player(con, playerID: str) -> list:
    """
    Gets the game IDs from the join table "ingame".

    In other words: gets the games a player is in.
    """
    return _get_game_or_player(con, playerID)


def get_players_in_game(con, gameID: int) -> list:
    """
    Gets the player IDs from the join table "ingame".

    In other words: gets all the players in a game.
    """
    return _get_game_or_player(con, gameID)


def shuffle(max_players: int = 4, human_readable: bool = False) -> tuple:
    """
    Returns a tuple of randomized turn orders
    to be paired with players.

    Example return data:
    (1, 0, 2, 3)

    And each players' order would then be stored in
    the ingame table with each player and hand.
    It's essentially drawing a ticket.

    Human readable: start turns at 1 instead of 0.
    """
    # start from 0 if human_readable is False,
    # otherwise start from 1 (1st, 2nd, 3rd, etc
    # instead of 0 meaning 1st, 1 meaning 2nd, and so on).
    order = list(range(max_players)) if not human_readable else list(range(1, max_players + 1))
    # although it would be good to keep things consistent
    # and to always start at 0, I plan to just compare values
    # for which is lesser or greater or to sort the list-UUID pairs
    # regardless, so it doesn't really matter

    # pair this shuffle function with
    # a list of player IDs like:
    # (h22Lab3, weh32ajd, 190aAApp, bmeQL24l)
    # and then store their turn with each
    # respective player
    random.shuffle(order)
    return tuple(order)

