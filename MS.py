import os
from typing import Optional
import json


class MS:
    def __init__(self, path: str, name: str = None, num_commits: int = None, team: str = None):
        self.path = path
        self.name = name if name else os.path.basename(os.path.normpath(path))
        self._num_commits = num_commits if num_commits else None
        self._team = team if team else None

    @property
    def num_commits(self) -> Optional[int]:
        return self._num_commits

    @num_commits.setter
    def num_commits(self, value: Optional[int]):
        self._num_commits = value

    @property
    def team(self) -> Optional[str]:
        return self._team

    @team.setter
    def team(self, value: Optional[str]):
        self._team = value

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if type(other) is str:
            return self.name == other
        return self.name == other.name

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return self.name


class MSEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, MS):
            return {"path": o.path, "name": o.name, "num_commits": o.num_commits, "team": o.team}
        return super().default(o)
