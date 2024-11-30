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
- playerID [str] (FOREIGN KEY)
- gameID [str] (FOREIGN KEY)

"""


def initialize_databases(database_connection):
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

    cur = database_connection.cursor()
    tables_res = cur.execute("SELECT name FROM sqlite_master")

    # "flattening" the table using itertools
    # and chain.from_terable. This makes it all
    # into a single list of items
    tables = tables_res.fetchall()
    temp_chain = chain.from_iterable(tables)
    tables = list(temp_chain)

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

    database_connection.commit()
    cur.close()


if __name__ == "__main__":
    logging.basicConfig(filename="server.log", level=logging.INFO, format=LOGGING_FORMAT)
    con = sqlite3.connect(DATA_DB)
    initialize_databases(con)

