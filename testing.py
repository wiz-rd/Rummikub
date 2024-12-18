#testing python

from dataclasses import dataclass, field
from typing import List


@dataclass
class Dance:
    name: str


@dataclass
class Oogway:
    boogway: str
    boogways: List[Dance] = field(default_factory=list)


d = Dance("party")
o = Oogway("WOOHOO", ["a", "oopo"])

print(d, o)
