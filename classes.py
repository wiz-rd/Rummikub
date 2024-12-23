from dataclasses import dataclass, field
from uuid import UUID, uuid4
from enum import Enum
import random


######################
# ABSOLUTE VARIABLES #
######################

# tile count should never exceed this many
# both for sanity and resources
MAX_TILE_COUNT: int = 1_000_000
MAX_POSSIBLE_PLAYERS: int = 6
MIN_POSSIBLE_PLAYERS: int = 4


##############
# DECORATORS #
##############


def add_enum_options(cls):
    """
    Adds an options() function that
    returns a list of all Enum options.
    """
    def options(cls):
        """
        Print the available Enum options
        sorted alphabetically.
        """
        opts = cls._member_names_
        opts.sort()
        return opts

    cls.options = classmethod(options)
    return cls


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
    
    cls.to_json = new_str
    return cls


#########
# ENUMS #
#########


@add_enum_options
class State(Enum):
    # NOTE: order these alphabetically
    ENDED = "The game has just finished."
    ONGOING = "The game is currently ongoing."
    PREGAME = "The game has not started yet."

@add_enum_options
class Color(Enum):
    """
    An enum to hold the possible colors.
    I may allow for changing to custom colors later.
    """
    # remember, order these alphabetically
    BLACK = "#000000"
    BLUE = "#00B9F2"
    ORANGE = "#FFB530"
    RED = "#FF2E17"

    def color_options():
        """
        Return Color options instead
        of a string of human-readable
        options.
        """
        return Color.BLACK, Color.BLUE, Color.ORANGE, Color.RED


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
    color: Color = Color.BLACK
    joker: bool = False
    # this could just be the number 0,
    # but a separate flag increases readability a ton.


# NOTE: API-exposed, if the person has the right creds
@dataclass
@to_json
class User:
    """
    Players, player data, and their scores.
    """
    id: UUID
    username: str
    email: str
    password: str
    last_login: str
    wins: int = 0
    losses: int = 0


    def __post_init__(self):
        """Have to generate a default uuid manually due to psuedo-randomness."""
        if self.id is None:
            self.id = uuid4().hex


@dataclass
@to_json
class Hand:
    """
    The hands and of each player. This should be stored with
    the table and NOT with the player.

    NOTE: The score is stored
    here as it's directly dependant on the hand and storing it
    with the player means in the DB, scores would be stored with players,
    which is undesirable
    """
    owner_id: UUID
    score: int = 0
    tiles: list[Tile] = field(default_factory=list)

    def update_score(self):
        """
        Updates the score but does
        NOT count jokers. Endgame = True
        does count the jokers as negative.

        Optimally, should only be called at the end of
        a game, but in case we decide to call it early,
        that's always an option.
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

    # # this value is purely for cosmetic purposes,
    # # but potentially we can use it for another scoring
    # # type at a later date
    # owner_id: str


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
    user_id: UUID
    hand: Hand


@dataclass
@to_json
class Game:
    """
    A class that stores statistics and values
    about the game as a whole.
    """

    #
    # these should be referenced individually
    # and stored in columns
    #
    id: UUID

    # stores whose turn it is in the game currently
    current_player_turn: UUID

    game_state: State = State.PREGAME
    table: Table = field(default_factory=Table)


    # ----------------------------------------------
    #
    # the rest should NOT be referenced individually
    # and should be stored as a part of the JSON blob
    # in the database
    #
    # E.g. it should be stored as gameData
    #

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

    def __post_init__(self):
        """Have to generate a default uuid manually due to psuedo-randomness."""
        if self.id is None:
            self.id = uuid4().hex

    def initialize(self, already_initialized: bool):
        """
        Initializes the game by performing all calculations,
        determining how many tiles to use, etc.
        """
        if not already_initialized:
                # clamp the max player count between 4 and 6
                if self.max_players < MIN_POSSIBLE_PLAYERS or self.max_players > MAX_POSSIBLE_PLAYERS:
                    # this should be caught on the frontend, but in case it's not
                    raise ValueError(f"Max player count must be between {MIN_POSSIBLE_PLAYERS} and {MAX_POSSIBLE_PLAYERS} inclusive.")

                # automatically set the joker count
                if self.joker_count < 0:
                    self.joker_count: int = 2 if self.max_players < 5 else 4

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

    def get_gamedata(self) -> str:
        """
        Returns all attributes as a string
        BUT skips the attributes with their own
        columns. These attributes are:

        - game_id
        - game_state
        - table
        - current_player_turn
        """
        json_to_return = self.__dict__.copy()
        # delete the values that are already stored in columns
        del json_to_return["id"]
        del json_to_return["game_state"]
        del json_to_return["table"]
        del json_to_return["current_player_turn"]

        str(json_to_return).replace("'", '"')
        return json_to_return

