import json
import random
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field

from litestar.dto import DTOConfig, DataclassDTO


######################
# ABSOLUTE VARIABLES #
######################

# tile count should never exceed this many
# both for sanity and resources
MAX_TILE_COUNT: int = 1_000
MAX_POSSIBLE_PLAYERS: int = 6
MIN_POSSIBLE_PLAYERS: int = 4


##############
# DECORATORS #
##############


def to_json(cls):
    """
    Modifies the __str__() function of the
    given class to print out a dictionary (as a string)
    of the given object, which should make
    saving things to a file a lot easier.
    """

    def new_str(self):
        """
        Returns the object's attirbutes as a
        dictionary converted to a string for
        use with JSON files. Quotes are converted
        to double quotes for this reason.
        """
        # swapping the quotes because JSON
        # prefers them to be double quotes
        return str(self.__dict__).replace("'", '"')
    
    cls.__repr__ = new_str
    return cls


#########
# ENUMS #
#########


STATES = [
    "ENDED",
    "ONGOING",
    "PREGAME"
]

COLORS = {
    "BLACK": "#000000",
    "BLUE": "#00B9F2",
    "ORANGE": "#FFB530",
    "RED": "#FF2E17",
}

GROUP_TYPES = [
    "RUN",
    "SET",
]


###########
# CLASSES #
###########


@dataclass
@to_json
class Tile:
    """
    Stores the number and color of a tile.
    """
    # default values - should be changed if needed.
    number: int = 0
    color: str = COLORS["BLACK"]
    joker: bool = False
    # this could just be the number 0,
    # but a separate flag increases readability a ton.


@dataclass
@to_json
class Hand:
    """
    The hands and of each player.

    Essentially a helper class to
    calculate score and store Tiles
    in a list.

    Scores WILL be calculated client
    side for displaying, but they should
    validate with the server for the final
    result (and intermittently) to avoid
    client manipulation.
    """
    score: int = 0
    tiles: list[Tile] = field(default_factory=list)

    def update_score(self):
        """
        Updates the score but does
        NOT count jokers. Endgame = True
        does count the jokers as negative.

        Optimally, should only be called at the end of
        a game, but it's possible to call it early.
        """
        self.score = 0

        for tile in self.tiles:
            self.score -= tile.number

            if tile.joker:
                self.score -= 30


@dataclass
@to_json
class Group:
    """
    A group of tiles in a run or set on the table.
    This is separate from a hand as it should
    remain on the table and be manipulatable.
    """
    tiles: list[Tile] = field(default_factory=list)

    def _valid(self) -> bool:
        """
        Returns a bool of whether
        or not this group is valid.
        """
        # if there are two few tiles,
        # it's already invalid
        if len(self.tiles) < 3:
            return False

        colors = list()
        self.is_set = True
        for tile in self.tiles:
            # check to see if there is
            # a tile of the same color
            # in the run - not allowed
            # if it's supposed to be a set
            try:
                colors.index(tile.color)
            except ValueError:
                # this is only suspected
                # and will need to be confirmed
                self.is_set = False

            colors.append(tile.color)

    def __post_init__(self):
        """
        Upon creation of the Group,
        validate it.
        """
        if not self._valid():
            raise ValueError("The group is not a valid set or run!")

    # # this value is purely for cosmetic purposes,
    # # but potentially we can use it for another scoring
    # # type at a later date
    # owner_id: UUID


@dataclass
@to_json
class Table:
    """
    Used to store information about the tiles on the table,
    including runs, sets, and the pool remaining.
    """
    pool: list[Tile] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)


@dataclass
@to_json
class IngameRow:
    """
    Stores the hands of each player
    and the position of each player.

    Essentially represents a row in the
    Ingame table.

    To add a player to a game, just add another
    row to the table with the same game ID and
    the new player's user ID.
    """
    game_id: UUID
    user_id: str
    hand: Hand | dict | str
    turnNumber: int

    def __post_init__(self):
        """
        Ran at the end of __init__
        of a dataclass. I'll use this
        to format the hand attribute
        automatically.
        """
        # checking for hand's type
        if isinstance(self.hand, Hand):
            pass
        elif isinstance(self.hand, dict):
            # if it's a dict, convert it
            # to a Hand
            self.set_hand(self.hand)
        elif isinstance(self.hand, str):
            # if it's a str, convert it to
            # a dict and then a Hand
            self.set_hand(json.loads(self.hand))
        else:
            # if it's none of them,
            # raise an issue
            raise ValueError(f"Hand value must be of type dict, str, or Hand.")

        # if it's any of the accepted types
        return

    def set_hand(self, d: dict) -> Hand:
        """
        Converts a (properly formatted) dictionary
        to a Hand object. Stores the Hand as
        self.hand and returns the Hand generated.
        """
        h = Hand()
        for key in d:
            # set the attribute of the
            # hand the key of the dictionary
            # ----
            # e.g. if the dictionary has the key
            # of "score", set the score
            # of h = to the value stored in d
            setattr(h, key, d[key])

        self.hand = h
        return h


@dataclass
@to_json
class GameSettings:
    """
    Create custom settings for a game.

    I'm unsure if I'll expose this to clients
    yet (if ever) but I figured I would
    implement a system for it just in case.
    """
    # time limit for turns in seconds
    # zero should be infinite
    turn_time_limit: int = 60
    starting_hand_count: int = 14

    # the minimum score that must be reached
    # by the first "move" of a player in order
    # for them to join the game.
    # NOTE: all tiles that add up to this score
    # have to come from the person's own hand.
    min_entry_meld_score: int = 30

    # this should be able to be changed
    max_players: int = 4
    joker_count: int = -1
    max_tile: int = 13
    min_tile: int = 1

    def initialize(self):
        # clamp the max player count between 4 and 6
        if self.max_players < MIN_POSSIBLE_PLAYERS or self.max_players > MAX_POSSIBLE_PLAYERS:
            # this should be caught on the frontend, but in case it's not
            raise ValueError(f"Max player count must be between {MIN_POSSIBLE_PLAYERS} and {MAX_POSSIBLE_PLAYERS} inclusive.")

        # automatically set the joker count
        if self.joker_count < 0:
            self.joker_count = 2 if self.max_players < 5 else 4

        # set_count is:
        # the amount of set,
        # min to max numbers,
        # in four colors

        # this SEEMS like a magic number, but basically,
        # the number needs to be divisible by 4, because
        # there are four colors in a game.

        # so to make the tile count appropriate to the amount of players
        # (which the tile count should be tiered to reflect), but not have
        # only a portion of the colors, you need either 2 sets of all colors
        # (8 total sets) or 3 sets of all colors (12 total sets of 1 - 13, if color is ignored)
        set_count = 8 if self.max_players < 5 else 12

        # 4 players have 8 sets of tiles ((2 groups of all 4 colors) = 8 groups numbered 1-13), and 5 players and up have 12 sets
        self.expected_tile_count: int = set_count * (self.max_tile - self.min_tile + 1) + self.joker_count

        if self.expected_tile_count > MAX_TILE_COUNT:
            raise ValueError(f"The tile count {self.expected_tile_count} is higher than the maximum count of {MAX_TILE_COUNT}.")


@dataclass
@to_json
class Game:
    """
    A class that stores statistics and values
    about the game as a whole.

    This can be created with particular settings
    by passing in a GameSettings object.
    """
    # these should be referenced individually
    # and stored in columns
    id: UUID = None

    # stores whose turn it is in the game currently
    current_player_turn: UUID = 0

    game_state: str = "PREGAME"
    table: Table = field(default_factory=Table)

    # should be used to delete the game if it hasn't
    # seen any activity in over x amount of days.
    # I'll probably do 3 days for PREGAME games
    # and 10 days for ONGOING games.
    # I don't know if I'll delete ENDED games yet
    # as I may just archive them.
    last_active: str = str(datetime.date(datetime.now()))

    # the user can pass a GameSettings obj
    # if they'd like custom game data
    game_data: GameSettings = GameSettings()

    def __post_init__(self):
        """
        Have to generate a default uuid manually due to psuedo-randomness.

        Additionally, initializes the GameSettings
        to calculate tile count and the like.
        """
        if self.id is None:
            self.id = uuid4().hex

        self.game_data.initialize()

    def db_list(self) -> list[str]:
        """
        Prepares a list that reflects the
        ER diagram for insertion into
        the database.
        """

        return [
            self.id,
            self.game_state,
            self.last_active,
            self.current_player_turn,
            self.table,
            self.game_data
        ]

    def start(self) -> bool:
        """
        Starts the game.

        Doles out hands to players,
        prepares the pool, and
        determines player order.

        Returns a bool of if the game
        was successfully started or not.
        Assumes the amount of players
        has been verified already.
        """
        # this should stop any future users from joining
        self.game_state = "ONGOING"

        # if the volume of tiles is too high
        # (preparation for if I ever add custom settings)
        if self.game_data.expected_tile_count > MAX_TILE_COUNT:
            raise ValueError(f"The tile count {self.game_data.expected_tile_count} is higher than the maximum count of {MAX_TILE_COUNT}.")

        # so to make the tile count appropriate to the amount of players
        # (which the tile count should be tiered to reflect), but not have
        # only a portion of the colors, you need either 2 sets of all colors
        # (8 total sets) or 3 sets of all colors (12 total sets of 1 - 13, if color is ignored)
        set_count = 8 if self.game_data.max_players < 5 else 12

        for _ in range(int(set_count / 4)):
            for color in COLORS.values():
                for num in range(self.game_data.min_tile, self.game_data.max_tile):
                    self.table.pool.append(Tile(number=num, color=color))

        # add the right amount of jokers with random colors
        for _ in range(self.game_data.joker_count):
            self.table.pool.append(
                Tile(
                    color=random.choice(list(COLORS.values())),
                    joker=True
                )
            )

        return True

    def dole_out_hands(self, players: list[IngameRow]) -> list[Hand]:
        """
        Doles out tiles from the pool
        into a list of Hand objects.

        Uses the game_data.starting_hand_count
        as reference for how many should
        be in each hand.
        """
        # the pool size but to be used as an index
        pool_size_index = len(self.table.pool) - 1
        hands = list()

        for i in range(self.game_data.max_players):
            for _ in range(self.game_data.starting_hand_count):
                # take a random tile from the pool
                tile: Tile = self.table.pool.pop(random.randint(0, pool_size_index))
                # put it in the player's hand
                players[i].hand.tiles.append(tile)
            # appending this to be returned
            hands.append(players[i].hand)
        # catch these (returned) hands
        return hands
        # this is a joke. Do not catch any thrown hands.
        # Hopefully no hands will be thrown.

    def draw_tile(self) -> Tile:
        """
        Draws a tile from the pool.
        """
        current_tile_count = len(self.table.pool)

        return self.table.pool.pop(random.randint(0, current_tile_count - 1))
