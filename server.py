import json
import sqlite3

from starlite import Starlite, MediaType, status_codes, get

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


# TODO: delete testing data
game = Game()
game.initialize(False)

insert_into_table(
    con,
    "games",
    [
        game.id,
        game.game_state,
        game.table.to_json(),
        game.current_player_turn,
        game.get_gamedata()
    ]
)

print(f"GameID - {game.id}")
print(f"Expected game url - http://localhost:8000/game/{game.id}")

# # testing the database:

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

# get_game_data(con, 1)
# print(get_games_with_player(con, "sampleid"))
# print(get_players_in_game(con, 1))


##########
# ROUTES #
##########

@get("/")
async def base_route() -> dict[str, str]:
    """
    Returns a simply success message indicating the
    API/server is functioning properly.
    """
    return {"reply": "success"}

@get("/game/{game_id:str}")
async def game_data(game_id: str) -> dict[str, str]:
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

    data = get_game_data(con, game_id)
    # TODO: figure out how to return with a 404
    # status code if a game isn't found?
    # convert all double quotes to single quotes
    # so they don't have to be escaped when
    # sent to the client
    data = [x.replace('"', "'") for x in data] if data is not None else "There is no game with that ID."
    return {"game_data": data}

app = Starlite(route_handlers=[base_route,game_data,])