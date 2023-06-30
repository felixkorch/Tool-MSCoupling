import MSDataParser as mdp
from Commit import *
from MS import *
import time
import concurrent.futures
import os
import json
import argparse


def __get_ms_logs(ms: MS, include_merges: bool = False) -> list[Commit]:
    return mdp.get_git_logs(ms, include_merges)


def parse_commits(path: str, output: str, include_merges: bool = False) -> None:
    start_time = time.monotonic()

    mss = mdp.get_ms_objects(path)
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