import json
import random
from uuid import UUID, uuid4
from datetime import datetime
from json import JSONDecodeError
from dataclasses import dataclass, field


######################
# ABSOLUTE VARIABLES #
######################

# tile count should never exceed this many
# both for sanity and resources
MAX_TILE_COUNT = 1_000
MAX_POSSIBLE_PLAYERS = 6
MIN_POSSIBLE_PLAYERS = 4


def convert_bools_for_json(data: str) -> str:
    """
    This gave me a lot of headache so I made
    a method, that way I can have even more
    headache when this also fails and I can't
    figure out why.
    """
    data = data.replace("False", "false")
    data = data.replace("True", "true")
    return data


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
        first_part = str(self.__dict__).replace("'", '"')
        return convert_bools_for_json(first_part)
    
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

    def construct_from_db(self, data: dict) -> None:
        """
        Constructs tiles from a dictionary.

        For use on a hand returned from the database and
        already constructed from the database output.
        """
        self.number = data["number"]
        self.color = data["color"]
        self.joker = data["joker"]


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

    def construct_from_db(self, data: str) -> None:
        """
        Modifies the current Hand object to reflect the database output.
        """
        # I'm so tired of this
        try:
            data = json.loads(data)
        except JSONDecodeError:
            data = convert_bools_for_json(data)
            data = json.loads(data)

        self.score = data["score"]

        for t in data["tiles"]:
            tile = Tile()
            tile.construct_from_db(t)
            self.tiles.append(tile)


@dataclass
@to_json
class Group:
    """
    A group of tiles in a run or set on the table.
    This is separate from a hand as it should
    remain on the table and be manipulatable.
    """
    tiles: list[Tile] = field(default_factory=list)

    def _is_set(self) -> bool:
        """
        Determines whether or not this
        group is a set.
        """
        # they are either the same number or a joker
        # calling an explicit equals so it's a bit clearer
        same_number = all([(x.number == self.tiles[0].number) or (x.joker == True) for x in self.tiles])
        used_colors = list()
        used_colors.append(self.tiles[0].color)

        if not same_number:
            return False

        for i, tile in enumerate(self.tiles):
            # if it's the first iteration
            if i == 0:
                continue

            # make sure each color is different
            # if any of them are the same,
            # it's not a valid set
            # unless that tile is a joker
            if tile.color in used_colors and not tile.joker:
                return False

        return same_number

    def _is_run(self, min_tile: int, max_tile: int) -> bool:
        """
        Determines whether or not this
        group is a run.
        """
        # making sure all colors are the same
        # by comparing each tile's color
        # to the first tile's color
        # making allowances for jokers
        all_same_color: bool = all([(x.color == self.tiles[0].color) or (x.joker == True) for x in self.tiles])

        if not all_same_color:
            # go ahead and skip any other check
            return False

        # get all joker tiles
        joker_tiles: list[Tile] = [x for x in self.tiles if x.joker]
        jokers_to_spare: bool = len(joker_tiles) > 0

        # make sure all joker tiles
        # are never falsely flagged as sequential
        for tile in joker_tiles:
            tile.number = min_tile - 10

        # get all non-joker tiles
        numbered_tiles: list[Tile] = sorted([x for x in self.tiles if not x.joker])

        # prepare a list to set the output to
        output_list: list[Tile] = list()

        # -------------------------
        # check if it's sequential
        for i, tile in enumerate(numbered_tiles):
            # skip the first check
            if i == 0:
                output_list.append(tile)
                continue

            next_tile: Tile = numbered_tiles[i - 1]

            # if it is one, it's sequential
            sequential: bool = abs(tile.number - next_tile.number) == 1

            if sequential:
                output_list.append(tile)
                continue

            # if NOT sequential
            # -----------------
            output_list.append(tile)

            # for use in calculating if there are
            # enough jokers to fill the gap
            current_num: int = tile.number

            # this should only be ran if
            # the sequential check failed
            # e.g. if there's a "gap" to be filled
            while True:
                jokers_to_spare: bool = len(joker_tiles) > 0
                local_seq: bool = abs(current_num - next_tile.number) == 1

                # if we've run out of jokers but it still isn't sequential
                if not local_seq and not jokers_to_spare:
                    return False
                # if we made it sequential, break
                # regardless of how many jokers are left
                elif local_seq:
                    break

                # if there are jokers
                # and it's not sequential
                # "use" the jokers to fill the spaces
                output_list.append(joker_tiles.pop())
                current_num += 1
            # once the gap is filled,
            # start over from the next numbered tile
            # to see if it's sequential to the following tiles
        # --------------------

        # just in case some funny business happened
        jokers_to_spare: bool = len(joker_tiles) > 0

        # --------------------
        # dole out remaining jokers

        # this WILL reorder user input
        # but only if they put jokers at the
        # beginning or end, so I'm okay with it,
        # at least for now
        if jokers_to_spare:
            # if there is enough "space" at the beginning
            # or end for all remaining jokers
            can_fit_at_end = len(jokers_to_spare) <= (max_tile - max(numbered_tiles))
            can_fit_at_beginning = len(jokers_to_spare) <= (min(numbered_tiles) - min_tile)

            # if there is a joker,
            # it IS sequential (see last check)
            # and there is no place for the extra jokers to go
            if not can_fit_at_end and not can_fit_at_beginning:
                return False
            elif can_fit_at_beginning and not can_fit_at_end:
                # put all unused jokers at the beginning
                self.tiles = joker_tiles + output_list
            elif can_fit_at_end and not can_fit_at_beginning:
                # put all unused jokers at the end
                self.tiles = output_list + joker_tiles
            # if it has neither the largest nor the smallest tiles
            elif can_fit_at_beginning and can_fit_at_end:
                # just default to putting the extras at the end
                self.tiles = output_list + joker_tiles
            # something went wrong
            else:
                return False
        else:
            # update hand to be sorted
            # so that users can't submit
            # hands out of order
            self.tiles = output_list
        # ------------------

        # if it survived the "sequential" gauntlet
        return all_same_color

    def is_valid(self, max_tile_number: int, min_tile_number: int) -> bool:
        """
        Returns a bool of whether
        or not this group is valid.
        """
        # if there are two few tiles,
        # it's already invalid
        if len(self.tiles) < 3:
            return False

        is_set = self._is_set()
        is_run = self._is_run(min_tile_number, max_tile_number)

        # return true if it's either a set OR a run
        return is_set or is_run

    def construct_from_db(self, data: str) -> None:
        """
        Constructs the current object to match the database
        when given a JSON string from said database.
        Same as all other construct_from_db methods.
        """
        # just in case there are any tiles already
        self.tiles.clear()

        # if it's a string,
        # convert it to JSON
        if isinstance(data, str):
            # let this err for debugging
            data = json.loads(data)
        elif not isinstance(data, dict):
            raise ValueError("Data to construct must be of type string.")

        for tile_str in data["tiles"]:
            tile = Tile()
            tile.construct_from_db(tile_str)
            self.tiles.append(tile)

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
    game_id: UUID = ""
    user_id: str = ""
    hand: Hand | dict | str = None
    turn_number: int = 0

    # def __post_init__(self):
    #     """
    #     Ran at the end of __init__
    #     of a dataclass. I'll use this
    #     to format the hand attribute
    #     automatically.
    #     """
    #     # checking for hand's type
    #     if isinstance(self.hand, Hand):
    #         pass
    #     elif isinstance(self.hand, dict):
    #         # if it's a dict, convert it
    #         # to a Hand
    #         self.set_hand(self.hand)
    #     elif isinstance(self.hand, str):
    #         # if it's a str, convert it to
    #         # a dict and then a Hand
    #         self.set_hand(json.loads(self.hand))
    #     else:
    #         # if it's none of them,
    #         # raise an issue
    #         raise ValueError(f"Hand value must be of type dict, str, or Hand.")

    #     # if it's any of the accepted types
    #     return

    def construct_from_db(self, data: str) -> None:
        """
        Updates this object to match the database.
        """
        # copying from the ER diagram:
        # userID, gameID, turnNumber, and hand
        self.user_id = data[0]
        self.game_id = data[1]
        self.turn_number = data[2]
        hand = Hand()
        data_parsed = convert_bools_for_json(data[3])
        hand.construct_from_db(data_parsed)
        self.hand = hand

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
    current_player_turn: int = 0

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

    def construct_from_db(self, contents: tuple[str] | list[str], columns: tuple[str] | list[str]) -> None:
        """
        Updates the object to match a game from the database.
        Requires a Game object to be created already so it can
        more easily be manipulated.

        Arguments: the raw responses from the server
        """
        game_dict = dict()

        for i, cl in enumerate(columns):
            # only converts the item in the list
            # to JSON if it's valid JSON
            # (i.e., not a string such as a UUID or game state)
            try:
                game_dict[cl] = json.loads(contents[i])
            except JSONDecodeError:
                game_dict[cl] = contents[i]

        # game-specific attributes
        self.id = game_dict["gameID"]
        self.game_state = game_dict["gameState"]
        self.last_active = game_dict["lastActive"]
        self.current_player_turn = game_dict["currentPlayerTurn"]

        # setting up the table
        table = game_dict["tableContents"]

        # convert from Pythonic true/falses
        # to JSON compatible t/f (so, lowercase)
        # I can't believe this is necessary
        # later: nevermind, it's user error - converting
        # an object to JSON manually can have its
        # consequences...
        if not isinstance(table, dict):
            try:
                table = json.loads(table)
            except JSONDecodeError:
                table = convert_bools_for_json(table)
                table = json.loads(table)

        self.table.pool = table["pool"]
        self.table.groups = table["groups"]

        # setting up game_data
        self.game_data.turn_time_limit = game_dict["gameData"]["turn_time_limit"]
        self.game_data.starting_hand_count = game_dict["gameData"]["starting_hand_count"]
        self.game_data.min_entry_meld_score = game_dict["gameData"]["min_entry_meld_score"]
        self.game_data.max_players = game_dict["gameData"]["max_players"]
        self.game_data.joker_count = game_dict["gameData"]["joker_count"]
        self.game_data.max_tile = game_dict["gameData"]["max_tile"]
        self.game_data.min_tile = game_dict["gameData"]["min_tile"]
        self.game_data.expected_tile_count = game_dict["gameData"]["expected_tile_count"]

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

        Prepares the pool.

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
        hands = list()

        for i in range(len(players)):
            for _ in range(self.game_data.starting_hand_count):
                # the pool size but to be used as an index
                pool_size_index = len(self.table.pool) - 1
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
