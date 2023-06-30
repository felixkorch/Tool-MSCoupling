import json
import subprocess
import os
import glob
import time


def get_nodes(data):
    repo_nodes = data['data']['organization']['team']['repositories']['nodes']
    nodes = []
    excluded = []
    for node in repo_nodes:
        if node['defaultBranchRef'] is None:
            print(f'Warning: {node["name"]} has no default branch, skipping')
            excluded.append('{:<100s}{}'.format(node['name'], 'has no default branch'))
            continue
        nodes.append({
            "commitCount": node['defaultBranchRef']['target']['history']['totalCount'],
            "name": node["name"],
            "languages": [n2['name'] for n2 in node["languages"]['nodes']],
            "files": [n['name'] for n in node['object']['entries']]
        })
    return nodes, excluded


# True if pass
def apply_filter(n) -> bool:
    if "ci-cd.yml" not in n['files']:
        return False
    return True


def apply_filter2(n) -> bool:
    if "pom.xml" not in n['files']:
        return False
    return True


def apply_filter3(n) -> bool:
    return n["commitCount"] > 50


def clone_repos(to_clone, where):
    dirs = next(os.walk(where))[1]
    to_remove = [dir for dir in dirs if dir not in to_clone]
    to_clone = [repo for repo in to_clone if repo not in dirs]
    print(f'{len(to_clone)} repos to clone')

    for repo_name in to_remove:
        print('Removing: ' + repo_name)
        subprocess.check_output(["rmdir", "/s", "/q", repo_name], cwd=f"./{where}", shell=True)

    non_existent_repos = []
    for repo_name in to_clone:
        try:
            d = subprocess.check_output(
                ["git", "clone", "-c", "core.longpaths=true",
                 f"GitHub-Org-Name/{repo_name}.git"],
                cwd=f'./{where}', shell=True)
        except:
            non_existent_repos.append(repo_name)
            continue

        print(d)
        print('Sleeping for 5 seconds...')
        time.sleep(5)
    if len(non_existent_repos) > 0:
        print(f'{len(non_existent_repos)} repos were not found on GitHub')
    return non_existent_repos


def main(argv):
    if len(argv) != 2:
        raise Exception('Provide 2 arguments')
    
    input_dir = argv[0]
    output_dir = argv[1]

    json_files = glob.glob(os.path.join(input_dir, '*.json'))
    all_nodes = []
    excluded = []
    included = []

    for file in json_files:
        f = open(file)
        data = json.load(f)
        inc, ex = get_nodes(data)
        all_nodes += inc
        excluded += ex
        f.close()

    for n in all_nodes:
        exclude_reasons = []
        if apply_filter(n) is False:
            exclude_reasons.append('ci-cd.yml missing')
        if apply_filter2(n) is False:
            exclude_reasons.append('pom.xml missing')
        if apply_filter3(n) is False:
            exclude_reasons.append('< 50 commits')
        if len(exclude_reasons) > 0:
            excluded.append('{:<100s}{}'.format(n['name'], '; '.join(exclude_reasons)))
        else:
            included.append(n['name'])

    removed_repos = clone_repos(included, output_dir)
    for repo_name in removed_repos:
        excluded.append('{:<100s}{}'.format(repo_name, 'Removed from GitHub'))
        included[:] = [name for name in included if name != repo_name]

    # Write included repos to file
    with open(os.path.join(input_dir, 'included.txt'), 'w') as fp:
        for item in included:
            fp.write("%s\n" % item)

    # Write included repos to file
    with open(os.path.join(input_dir, 'excluded.txt'), 'w') as fp:
        for item in excluded:
            fp.write("%s\n" % item)