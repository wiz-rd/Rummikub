#!/usr/bin/python3

"""
NOTE: This is just a proof of concept and
is deliberately only text-based. It's not
meant to be a final product at all, it's
just to help me get used to what I'll have to do.

Most likely, I'll be writing a lot of the code in JavaScript
and/or making an API in Python. I will NOT
be coding the whole thing in Python as I would like
to make this a website.

Rules URL: https://rummikub.com/wp-content/uploads/2019/12/2600-English-1.pdf
"""

import json
import random
from enum import Enum
from uuid import uuid4
from typing import List
from dataclasses import dataclass, field


"""

Some notes:

Store the game state in files!!! Or something similar. If I store it in RAM,
it would be really easy to take down the server. It can still be taken down by DoS attacks
even if I save it into files, but they would have to be more coordinated and it's less likely to happen
simply due to traffic. Not that I expect any more traffic than literally just us, but I digress.
This means that the only part of the game stored in RAM is on the client's side, presumably in their
browser.

When a game ends, players with tiles in their hand LOSE points relative to that score.
But, in a needlessly convuluted manner, the winner GAINS the TOTAL points everyone else loses
by having tiles in their hand. Sick.

I need to store the state of the table BEFORE a turn begins, because if a player reaches the time
limit, then everything needs to be returned to how it was before (and a tile needs to be given to them
as their turn ends).

"""





"""
NOTE Some definitions

WinCon / Win Condition: the condition to be met to win the game. Kind of like a metric.

Meld: A "set" or group of tiles, whether it be a run, set, etc.

"""

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


def change_str_to_dict(cls):
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
    
    cls.__str__ = new_str
    return cls


#########
# ENUMS #
#########


@add_enum_options
class WinConditions(Enum):
    # NOTE:
    # always order these alphabetically, even here.
    EMPTY_HAND = "Win the game by emptying your whole hand. Points are ignored unless a tie needs to be broken."
    HIGHEST_SCORE = "Win the game by having the highest score after _anyone_ places their last tile."

@add_enum_options
class State(Enum):
    # NOTE: same as above - order these alphabetically
    ENDED = "The game has just finished"
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
@change_str_to_dict
class Tile:
    """
    Stores the number and color of a tile.
    """
    # default values - should be changed.
    number: int = 0
    color: Color = Color.BLACK
    joker: bool = False
    # this could just be the number 0,
    # but having a separate flag allows for
    # custom number ranges... something that'll
    # probably never be used B)
    # it also increases readability a ton.


@dataclass
@change_str_to_dict
class Player():
    """
    Individual players and their score.
    """
    name: str = ""
    score: int = 0

    # where they are on the table.
    # defaults to 0 but should change
    # based on the other players' positions.
    # random values should be default but there
    # could also exist an option to manually
    # move poeple around.
    position: int = 0

    # generate a uuid for the player
    uuid: str = ""

    def __post_init__(self):
        self.uuid = uuid4().hex


@dataclass
@change_str_to_dict
class Hand:
    """
    Stores information about the current player's hand.
    """
    # the total score of their hand
    # to be used for score calculations later
    score: int = 0
    tiles: List[Tile] = field(default_factory=list)

    # use a UUID instead of an object
    # to be able to store it in a file easily
    # and also more easily expose it to the right person
    player_uuid: str = ""

    def update_score(self, endgame: bool = False):
        """
        Updates the score but does
        NOT count jokers. Endgame = True
        does count the jokers.
        """
        self.score = 0

        if endgame:
            for tile in self.tiles:
                self.score -= tile.number

                if tile.joker:
                    self.score -= 30
        else:
            for tile in self.tiles:
                self.score += tile.number

    def endgame_update_score(self):
        """
        Updates the score and counts jokers.
        Wrapper for update_score() with endgame as true.
        """
        self.update_score(endgame=True)
    
    def beautify_hand(self):
        """
        Returns a string of the data in the hand
        but in a human-readable format.
        """
        
        str_uuid = f"Player UUID: {self.player_uuid}"
        str_tiles = ""
        for t in self.tiles:
            str_tiles += f"{t.number}\t{t.color}\n"
        return f"\n{str_uuid}\n{str_tiles}"



@dataclass
@change_str_to_dict
class Group:
    """
    A group of tiles in a run or set on the table.
    This is separate from a hand as it should
    remain on the table.
    """
    tiles: List[Tile] = field(default_factory=list)
    # a relatively useless value that would only
    # be used for visual purposes. I probably won't
    # use it, though.
    owner_uuid: str = ""
    # whether or not it's a run or set
    run: bool = False


@dataclass
@change_str_to_dict
class Table:
    """
    Used to store information about the tiles on the table,
    including runs, sets, and the pool remaining.
    """
    pool: List[Tile] = field(default_factory=list)
    hands: List[Hand] = field(default_factory=list)


@dataclass
@change_str_to_dict
class Game:
    """
    The "table" at a current state and various other
    statistics about the game.
    """
    win_condition: WinConditions = WinConditions.HIGHEST_SCORE
    state: State = State.PREGAME
    table: Table = field(default_factory=Table)
    players: List[Player] = field(default_factory=list)

    # whether or not the game has been initialized.
    # it can only be done once
    initialized: bool = False

    # this is in seconds
    # setting it equal to zero
    # should make it infinite.
    turn_time_limit: float = 60

    # how many tiles everyone starts with
    starting_hand_count: int = 14

    # the minimum score that must be reached
    # by the first "move" of a player in order
    # for them to join the game.
    # NOTE: all tiles that add up to this score
    # have to come from the person's own hand.
    min_entry_meld_score: int = 30

    # this can be raised but it will change
    # the tile count. The MINIMUM number that this
    # should be is 4
    max_players: int = 4

    # the highest and number a tile can go to
    # (the minimum is always 1)
    min_tile: int = 1
    # the tile count is relative to this number
    max_tile: int = 13

    joker_count: int = -1


    def overview(self) -> dict:
        """
        Returns the same thing as the initialize function,
        just doesn't perform any actions and can thus be called
        multiple times.
        """
        return self._initialize_and_overview_(already_initialized = True)

    def initialize(self) -> dict:
        """
        Wrapper for internal method:

        Initializes the game by performing all calculations,
        determining how many tiles to use, etc. Returns
        statistics about the game.

        Can only be called once per game.
        """
        return self._initialize_and_overview_(self.initialized)

    def _initialize_and_overview_(self, already_initialized: bool = True) -> dict:
        """
        Internal method to save some code. Either initializes the game
        or returns stats about it.

        Initializes the game by performing all calculations,
        determining how many tiles to use, etc. Returns
        statistics about the game.
        """

        # if this is the FIRST TIME
        if not already_initialized:
            self.max_players = len(self.players)

            # clamp the max player count between 4 and 6
            if self.max_players < MIN_POSSIBLE_PLAYERS or self.max_players > MAX_POSSIBLE_PLAYERS:
                # this should be caught on the frontend, but in case it's not
                raise ValueError(f"Max player count must be between {MIN_POSSIBLE_PLAYERS} and {MAX_POSSIBLE_PLAYERS} inclusive.")


            # if no unique count is given or a  number is less
            # than zero, which is, of course, impossible, then
            # automatically set the joker count
            if self.joker_count < 0:
                self.joker_count: int = 2 if self.max_players < 5 else 4

            # the amount of sets:
            # min to max numbers
            # in four colors

            # this SEEMS like a magic number, but basically,
            # the number needs to be divisible by 4, because
            # there are four colors in a game.

            # so to make the tile count appropriate to the amount of players
            # (which the tile count should be tiered to reflect), but not have
            # only a portion of the colors, you need either 2 sets of all colors
            # (8 total sets) or 3 sets of all colors (12 total sets of 1 - 13, if color is ignored)
            set_count = 8 if self.max_players < 5 else 12

            # NOTE: THIS DEVIATES FROM THE RULES
            # what I'm doing is making tile count relative to the player count.
            # while the rules DO do this, this allows for a bit more
            # fluidity as the rules have kind of "steps/tiers" for player counts,
            # but this instead just calculates a number based on player count

            # 4 players have 8 sets of tiles ((2 groups of all 4 colors) = 8 groups numbered 1-13), and 5 players and up have 12 sets
            self.expected_tile_count: int = set_count * (self.max_tile - self.min_tile + 1) + self.joker_count

            if self.expected_tile_count > MAX_TILE_COUNT:
                raise ValueError(f"The tile count {self.expected_tile_count} is higher than the maximum count of {MAX_TILE_COUNT}.")


            # generate all tiles
            for _ in range(int(set_count / 4)):
                for color in Color.color_options():
                    print(color)
                    for num in range(self.min_tile, self.max_tile + 1):
                        self.table.pool.append(Tile(number=num, color=color))

            # add randomized jokers dynamically
            for _ in range(self.joker_count):
                # add random-colored jokers to the pool
                # it's okay if they're the same color, it's no biggie
                self.table.pool.append(Tile(color=random.choice(Color.color_options()), joker=True))

            self.initialized = True


        return {
            "Expected Tiles": self.expected_tile_count,
            "Actual Tiles": len(self.table.pool),
            "Max Players": self.max_players,
            "Jokers": self.joker_count,
            "Tile Range": f"{self.min_tile} - {self.max_tile}",
            "Win Condition": self.win_condition.name,
        }
    
    def add_player(self, player):
        """
        Adds the given player to a list of players
        in the current game.
        """
        self.players.append(player)
    
    def randomize_positions(self):
        """
        Randomizes the positions of each player.
        Should be called when a game is started
        and/or initialized. This DOES work even
        if the player count doesn't exactly match
        the min max player count (for example, 3).
        """
        pos_opts = list(range(self.max_players))
        # set them to a random position and then
        # remove that option from the pool
        for player in self.players:
            pos = random.choice(pos_opts)
            player.position = pos
            pos_opts.remove(pos)

    def dole_out_hands(self):
        """
        Generate and apply hands from the table pool.
        """
        # create a hand for each player
        for player in self.players:
            self.table.hands.append(Hand(player_uuid=player.uuid))    

        # grab a choice from the pool
        # and give them to each hand,
        # subsequently removing them
        # from the pool afterwards.
        for hand in self.table.hands:
            for _ in range(self.starting_hand_count):
                tile = random.choice(self.table.pool)
                hand.tiles.append(tile)
                self.table.pool.remove(tile)



if __name__ == "__main__":
    game = Game()

    # create players
    player1 = Player(name="Ben")
    player2 = Player(name="Sarah")
    player3 = Player(name="Victoria")
    player4 = Player(name="Nina")

    # add them to the game
    game.add_player(player1)
    game.add_player(player2)
    game.add_player(player3)
    game.add_player(player4)

    # initialize the game
    # and print data
    print(game.initialize())

    # randomize player positions
    game.randomize_positions()
    game.dole_out_hands()
    for hand in game.table.hands:
        print(hand.beautify_hand())

