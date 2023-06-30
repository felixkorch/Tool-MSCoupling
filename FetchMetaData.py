import requests
import json, os, time


# Runs a query to fetch metadata for a given org_name and team_slug (system)
def do_query(org_name, team_slug, token, cursor):

    req_headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }

    query = """
        query MetaData($team: String!, $org: String!, $cursor: String) {
          organization (login: $org) {
                team(slug: $team) {
                  name
                  repositories(first:100, after: $cursor) {
                    pageInfo {
                      endCursor
                      hasNextPage
                    }
                    nodes {
                      object(expression: "HEAD:") {
                        ... on Tree {
                          entries {
                            name
                          }
                        }
                      }
                      defaultBranchRef {
                        target {
                          ... on Commit {
                            history {
                              totalCount
                            }
                          }
                        }
                      }
                      name

                    }
                    totalCount
                  }
                }
              }
            }
        """

    params = {"team": team_slug, "org": org_name, "cursor": cursor}
    response = requests.post('https://api.github.com/graphql', headers=req_headers, json={'query': query, 'variables': params})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed to run with a {response.status_code}. {response.text}")


# Returns the cursor for the next page and a boolean indicating if there is a next page
def get_next(data):
    page_info = data['data']['organization']['team']['repositories']['pageInfo']
    return page_info['endCursor'], page_info['hasNextPage']


# Fetches metadata for a given team_slug (system) and saves it to a JSON file
def get_metadata(org_name, team_slug, token, cursor=""):
    has_next = True
    page_nr = 1
    file_name = f"page{page_nr}.json"
    out_dir = f"./{team_slug}_JSON"

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    while has_next:
        try:
            data = do_query(org_name, team_slug, token, cursor)
            with open(os.path.join(out_dir, file_name), "w") as outfile:
                json.dump(data, outfile)
            cursor, has_next = get_next(data)
            time.sleep(5)
        except Exception as e:
            print(f"Request failed, maybe points ran out\tcursor: {cursor}")
            print(f"Error: {str(e)}")
            break
        page_nr += 1
        file_name = f"page{page_nr}.json"
        print(f"cursor: {cursor}")