import re
import subprocess
from typing import List
from pathlib import Path
from Commit import *
from MS import *
import time
import concurrent.futures
import os
import json
import argparse
# This module contains functions for parsing Git-log data from the command line.
# The intended output is a list of Commit objects, which can be used to create a JSON file.

# compile the regular expression for matching the line data
line_data_regex = re.compile(r'^\s*(\d+)\s+(\d+).*$')


def get_ms_objects(path: str) -> List[MS]:
    # get a list of subdirectories in the given path
    subdirs = [x for x in Path(path).iterdir() if x.is_dir()]

    # create an MS object for each subdirectory that is a Git repository
    ms_objects = []
    for subdir in subdirs:
        if os.path.exists(os.path.join(subdir, ".git")):
            # if the subdirectory is a Git repository, create an MS object for it
            ms_path = str(subdir)
            ms_object = MS(path=ms_path)
            ms_objects.append(ms_object)

    # return the list of MS objects
    return ms_objects


# Function for parsing the git-log data from the command line, using subprocess
# It parses all the information needed to create a Commit object
# It returns a list of Commit objects, which can be used to create a JSON file
def get_git_logs(ms: MS, include_merge=True) -> list[Commit]:
    # Specify git log command
    if not include_merge:
        cmd = ['git', 'log', '--no-merges', '--reverse', '--pretty=format:---COMMIT---%n%H,%at,%an', '--numstat']
    else:
        cmd = ['git', 'log', '--reverse', '--pretty=format:---COMMIT---%n%H,%at,%an', '--numstat']

    # Execute command and split output into individual commits
    commits = subprocess.check_output(cmd, cwd=ms.path, universal_newlines=True, encoding='utf-8').strip().split(
        '---COMMIT---')

    # Filter out empty commits and split each commit into lines
    commits = [commit.strip().split('\n') for commit in commits if commit.strip()]

    # Parse each commit and create a Commit object
    logs = [__parse_commit(commit, ms) for commit in commits]

    ms.num_commits = len(logs)
    return logs


def __parse_commit(commit: list[str], ms: MS) -> Commit:
    # Extract and parse commit metadata
    hash, unix_time, author = commit[0].split(',')
    unix_time = int(unix_time)

    # Extract and parse numstat data
    lines_data = commit[1:]
    lines_added, lines_removed = __parse_lines_data(lines_data)

    return Commit(hash=hash, unix_time=unix_time, author=author, lines_added=lines_added, lines_deleted=lines_removed,
                  ms=ms)


def __parse_lines_data(lines_data: list[str]) -> tuple[int, int]:
    lines_added = lines_removed = 0
    for line in lines_data:
        match = line_data_regex.match(line)
        if match:
            lines_added += int(match.group(1))
            lines_removed += int(match.group(2))
    return lines_added, lines_removed


def __get_ms_logs(ms: MS, include_merges: bool = False) -> list[Commit]:
    return get_git_logs(ms, include_merges)


def parse_commits(path: str, output: str, include_merges: bool = False) -> None:
    start_time = time.monotonic()

    mss = get_ms_objects(path)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        logs = list(executor.map(__get_ms_logs, mss, [include_merges] * len(mss)))

    all_commits = [item for sublist in logs for item in sublist]
    all_commits = sorted(all_commits, key=lambda commit: commit.unix_time)

    # create 'commits' folder if it doesn't exist
    if not os.path.exists('commits'):
        os.mkdir('commits')

    # save all_commits to a JSON file
    with open(f'commits/{output}.json', 'w') as f:
        json.dump(all_commits, f, indent=2, cls=CommitEncoder)

    end_time = time.monotonic()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.2f} seconds")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, required=True, help="Path to MS folder")
    parser.add_argument("--output", type=str, required=True, help="Path to output file")
    args = parser.parse_args()
    parse_commits(args.path, args.output)


if __name__ == '__main__':
    main()