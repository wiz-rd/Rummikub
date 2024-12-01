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

import json
import random
import sqlite3
import logging
from uuid import uuid4
from itertools import chain

from rummikub import *


DATA_FOLDER = "./data"
# NOTE: please see above regarding credentials
DATA_DB = f"{DATA_FOLDER}/data.db"
LOGGING_FORMAT = "%(asctime)s — %(levelname)s — [%(filename)s] -> %(message)s"
logger = logging.getLogger(__name__)

"""
This is a brief outline of the database and what
tables and other contents it'll contain.

Tables:
- Games
- Users
- Ingame

#######################################################

Users Table:
- uuserID [TEXT] (PRIMARY KEY)
- userName [TEXT]
- email [TEXT]
- password [TEXT]

Emails will NOT be used, and likely won't even be collected to avoid being breached.
It would literally only be a preventative measure for DoS'ing or spamming
the database. Having a hash of them could prevent making multiple accounts
with the same email, hence this field.

- wins [TEXT]
- losses [TEXT]

Perhaps I shouldn't consider losses that much, as it's super easy to
lose this game and it's not luck based. Additionally, it doesn't show skill
or something that much - like, it feels a bit like a useless number. I'll still
add it for edge cases or in case people get real competative with it.

- lastLogon

#######################################################

Games Table:
- gameID [int] (PRIMARY KEY - should just be an integer)
- gameState [TEXT]
- tablePool [TEXT (json)] NOTE: SQLite does not have list objects
- tableHands [TEXT (json)]
- groups [TEXT (json)] NOTE: this stores the sets and runs on the table

NOTE: Should dole out hands upon request BUT
should have some measures to prevent it from
overloading itself and/or corrupting the DB by
making a ton of calls (potentially simultaneous) to it.

NOTE: the game should be able to be entirely reconstructed
from an entry in the Games table, one way or another. Also, NOTE that
the hands are stored as a subset of the table, so they aren't stored independently.

#######################################################

(JOIN TABLE)

NOTE: This table stores WHO is in a game and WHAT games they're in.
It's a join table to handle a many-to-many relationship between
players and games.

Ingame Table:
- gameID [str] (FOREIGN KEY)
- playerID [str] (FOREIGN KEY)

"""


def initialize_db_and_tables(con) -> None:
    """
    Creates the database if there isn't one already
    and adds the appropriate tables etc.
    """

    req_tables_and_queries = {
        "games": """CREATE TABLE games(
        gameID INTEGER,
        gameState TEXT,
        tablePool TEXT,
        tableHands TEXT,
        groups TEXT,
        PRIMARY KEY(gameID DESC));""",

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
        con.close()
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


if __name__ == "__main__":
    """
    NOTE: make sure to close each connection after it's
    served its purpose. This should hopefully save on resources.
    """
    logging.basicConfig(filename="server.log", level=logging.INFO, format=LOGGING_FORMAT)
    con = sqlite3.connect(DATA_DB)
    initialize_db_and_tables(con)
    # insert_into_table(
    #     con,
    #     "users",
    #     ["sampleid",
    #      "sample_username",
    #      "sampleemail",
    #      "samplepassword",
    #      "1",
    #      "0",
    #      "yesterday"])

    get_game_data(con, 1)
    print(get_games_with_player(con, "sampleid"))
    print(get_players_in_game(con, 1))

