from starlite import Starlite, get


"""
To run this, run:

uvicorn starlite_practice:app

Note that uvicorn/starlite have this as:

uvicorn starlite_practice:app --reload
"""


@get("/")
async def hello_world() -> dict[str, str]:
    """Keeping the tradition alive with hello world."""
    return {"hello": "world"}


@get("/game/{gameid:str}")
def list_players_game(gameid: str) -> dict[str, list[str]]:
    """Returns the players in a game."""
    return {"players": [gameid]}


@get("/players")
def list_players() -> dict[str, list[str]]:
    """Returns the players in a game."""
    return {"players": [""]}


app = Starlite(route_handlers=[hello_world,list_players,list_players_game])
