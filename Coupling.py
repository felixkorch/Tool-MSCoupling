
from Commit import Commit
from MS import MS
from itertools import combinations
from ClusteringMethod import DBSCANClustering
from datetime import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import DBSCAN
from time import perf_counter


class ClusterIndex:
    def __init__(self, clusters: list[list[Commit]], clusters_per_day=None):
        self.clusters = clusters
        self.index: dict[MS, set[int]] = {}
        self.clusters_per_day = clusters_per_day

    # Creates an inverted index of Microservice to the clusters they occur in
    def create_index(self):
        for idx, cluster in enumerate(self.clusters):
            for commit in cluster:
                if commit.ms not in self.index:
                    self.index[commit.ms] = {idx}
                else:
                    self.index[commit.ms].add(idx)

    def get_internal_index(self):
        return self.index

    def get_clusters(self) -> list[list[Commit]]:
        return self.clusters

    def get_clusters_per_day(self):
        return self.clusters_per_day

    def __get_sorensen_coef(self, msx_set, msy_set) -> float:
        return len(msx_set & msy_set) * 2 / (len(msx_set) + len(msy_set))

    def __get_jaccard_index(self, msx_set, msy_set) -> float:
        return len(msx_set & msy_set) / len(msx_set | msy_set)

    def __get_active_period(self, msx, msy):
        intersection = self.index[msx] & self.index[msy]
        if not intersection:
            return "TBD to TBD"
        start_date = self.clusters[min(intersection)][0].unix_time
        end_date = self.clusters[max(intersection)][0].unix_time
        return f"{datetime.fromtimestamp(start_date).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(end_date).strftime('%Y-%m-%d')}"

    def __get_coupling(self, nCr: list[tuple], scoring_method):
        scoring_fn = {'sorensen': self.__get_sorensen_coef,
                      'jaccard': self.__get_jaccard_index}
        if scoring_method not in scoring_fn:
            raise Exception(
                f"Scoring method: '{scoring_method}' is not supported")

        return [
            {
                'msx': c[0],
                'msy': c[1],
                'len_x': len(self.index[c[0]]),
                'len_y': len(self.index[c[1]]),
                'len_intersect': len(self.index[c[0]] & self.index[c[1]]),
                'len_union': len(self.index[c[0]] | self.index[c[1]]),
                'score': scoring_fn[scoring_method](self.index[c[0]], self.index[c[1]]),
                'active_period': self.__get_active_period(c[0], c[1])
            }
            for c in nCr
        ]

    # Gets top n most coupled in index
    def get_all_couplings(self, scoring_method='jaccard') -> pd.DataFrame:
        mss: list[MS] = list(self.index.keys())
        combs = [(mss[c[0]], mss[c[1]]) for c in combinations([*range(0, len(mss))], 2)]

        if len(combs) == 0:
            return pd.DataFrame(columns=['msx', 'msy', 'len_x', 'len_y', 'len_intersect', 'len_union', 'score', 'norm_support', 'active_period'])

        df = pd.DataFrame(self.__get_coupling(nCr=combs, scoring_method=scoring_method))
        df['norm_support'] = df['len_intersect'] / np.percentile(df['len_intersect'], 99)
        return df

    # Gets top couplings for a specific MS
    def get_coupling_for(self, msX, scoring_method='jaccard'):
        nCr = [(msX, msY) for msY in self.index.keys() if msY != msX]
        return self.__get_coupling(nCr=nCr, scoring_method=scoring_method)


# Gets coupling scores for each pair of microservices over time.
# Monthly, cumulative
def get_coupling_cumulative(commits: list[Commit], eps="4h"):
    cl = DBSCANClustering(eps=eps)
    clusters_ids = cl.run_inverted(commits)

    df = pd.DataFrame({'commit': commits, 'cluster_id': clusters_ids})
    df['date'] = df['commit'].apply(lambda x: datetime.fromtimestamp(x.unix_time))

    coupling_dfs = []
    clusters = []

    for _, group in df.groupby(pd.Grouper(key="date", freq="1M")):
        if len(group) > 0:  # check if group is not empty
            monthly_clusters = group.groupby('cluster_id')['commit'].apply(list).tolist()
            clusters.extend(monthly_clusters)

        index = ClusterIndex(clusters)
        index.create_index()
        coupling_dfs.append(index.get_all_couplings(scoring_method='jaccard'))


def get_coupling_data(commits: list[Commit], eps="4h"):

    time_start = perf_counter()

    commits_np = np.array(commits).reshape(-1, 1)
    unix_times = np.array([c.unix_time for c in commits]).reshape(-1, 1)
    dbscan = DBSCAN(eps=DBSCANClustering.parse_time_str(eps), min_samples=1).fit(X=unix_times)

    # Calculate clusters per day
    cluster_ids = list(cluster_id for cluster_id in dbscan.labels_ if cluster_id != -1)
    df = pd.DataFrame({'commit': commits, 'cluster_id': cluster_ids})
    df['date'] = df['commit'].apply(lambda x: datetime.fromtimestamp(x.unix_time))
    df_days = df.groupby(pd.Grouper(key='date', freq='1D')).agg(unique_clusters=('cluster_id', pd.Series.nunique))
    df_days = df_days[df_days['unique_clusters'] > 0]
    clusters_per_day = df_days['unique_clusters'].mean()

    # Calculate clusters
    clusters = [list(commits_np[np.where(np.equal(dbscan.labels_, i))][:, 0])
                for i in set(dbscan.labels_) if i != -1]

    index = ClusterIndex(clusters=clusters, clusters_per_day=clusters_per_day)
    index.create_index()

    time_elapsed = perf_counter() - time_start
    return index.get_all_couplings(), {'clusters_per_day': clusters_per_day, 'time_elapsed': time_elapsed}


def plot_score_norm_matrix(provided_df):
    score_bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    norm_support_bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, float('inf')]
    labels = ['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0', '> 1.0']

    provided_df['score_range'] = pd.cut(provided_df['score'], bins=score_bins, labels=labels[:-1])
    provided_df['norm_support_range'] = pd.cut(provided_df['norm_support'], bins=norm_support_bins, labels=labels)

    # Create a cross-tabulation
    cross_tab = pd.crosstab(provided_df['score_range'], provided_df['norm_support_range'], dropna=False)

    # Reindex the cross-tabulation to include all ranges
    cross_tab = cross_tab.reindex(index=labels[:-1], columns=labels, fill_value=0)

    # Convert cross-tabulated values to log-scale
    log_scale_cross_tab = np.log1p(cross_tab)  # log1p = log(1 + x), to avoid log(0)

    # Plot the heatmap
    plt.figure(figsize=(7, 5))  # Adjusted figure size to fit the larger heatmap
    sns.heatmap(log_scale_cross_tab, annot=cross_tab.values, cmap="YlGnBu", fmt='d', annot_kws={"fontsize": 8})

    plt.title('Co-occurrence of Score and Norm Support Ranges')
    plt.xlabel('Norm Support Range')
    plt.ylabel('Score Range')

    plt.show()