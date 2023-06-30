import json
import os
import glob
import pandas as pd


def get_nodes(data):
    repo_nodes = data['data']['organization']['team']['repositories']['nodes']
    nodes = []
    for node in repo_nodes:
        if node['defaultBranchRef'] is None:
            print(f'Warning: {node["name"]} has no default branch, skipping')
            continue
        nodes.append({
            "commitCount": node['defaultBranchRef']['target']['history']['totalCount'],
            "name": node["name"],
            "files": [n['name'] for n in node['object']['entries']]
        })
    return nodes


# True if pass
def apply_filter(n, forks) -> bool:
    if "ci-cd.yml" not in n['files']:
        return False
    if "pom.xml" not in n['files']:
        return False
    if n["commitCount"] <= 50:
        return False
    if n['name'] in forks:
        return False
    return True


def main(argv):
    if len(argv) != 1:
        raise Exception('Provide 1 argument')

    dir = argv[0]

    json_files = glob.glob(os.path.join(dir, '*.json'))
    all_nodes = []

    for file in json_files:
        with open(file) as f:
            data = json.load(f)
            inc = get_nodes(data)
            all_nodes += inc

    total_commits_before = sum(n['commitCount'] for n in all_nodes)
    total_files_before = sum(len(n['files']) for n in all_nodes)
    stats = {
        'Total Repositories Before Filtering': len(all_nodes),
        'Total Commits Before Filtering': total_commits_before,
        'Total Files Before Filtering': total_files_before,
    }

    with open(os.path.join(dir, 'forks.txt'), 'r') as f:
        forks = [line.split(' is a fork of ')[0] for line in f]

    all_nodes = [n for n in all_nodes if apply_filter(n, forks)]
    stats['Total Repositories After Filtering'] = len(all_nodes)
    stats['Total Commits After Filtering'] = sum(n['commitCount'] for n in all_nodes)
    stats['Total Files After Filtering'] = sum(len(n['files']) for n in all_nodes)

    df = pd.DataFrame([stats])
    df.to_excel(os.path.join(dir, 'repo_stats.xlsx'), index=False)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
