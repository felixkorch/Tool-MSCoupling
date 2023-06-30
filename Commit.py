from dataclasses import dataclass
from MS import MS, MSEncoder
import json
from datetime import datetime
import bisect


@dataclass
class Commit:
    hash: str
    unix_time: int
    author: str
    lines_added: int
    lines_deleted: int
    ms: MS

    # Comparisons based on time
    def __lt__(self, nxt):
        return self.unix_time < nxt.unix_time

    def __hash__(self):
        return hash(self.hash)


class CommitEncoder(json.JSONEncoder):
    def __init__(self, ms_encoder=MSEncoder, **kwargs):
        super().__init__(**kwargs)
        self.ms_encoder = ms_encoder

    def default(self, o):
        if isinstance(o, Commit):
            return {
                "hash": o.hash,
                "unix_time": o.unix_time,
                "author": o.author,
                "lines_added": o.lines_added,
                "lines_deleted": o.lines_deleted,
                "ms": self.ms_encoder().default(o.ms)
            }
        return super().default(o)


def get_commits_before(commits: list[Commit], date: datetime):
    unix_time = date.timestamp()
    # Perform binary search to find the index
    index = bisect.bisect_right(commits, unix_time, key=lambda obj: float(obj.unix_time))
    return commits[:index]


def load_commits(file_path: str) -> list[Commit]:
    # read JSON file containing list of commits
    with open(file_path, 'r') as f:
        commits_list = json.load(f)

    # convert each dict in list to Commit object
    all_commits = []
    for commit_dict in commits_list:
        # create MS object from nested dict in commit_dict
        ms_dict = commit_dict.pop('ms')
        ms = MS(**ms_dict)
        # create Commit object and append to list
        commit = Commit(ms=ms, **commit_dict)
        all_commits.append(commit)

    return all_commits