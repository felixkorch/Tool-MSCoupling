import pandas as pd

from Commit import Commit

from datetime import datetime
from scipy.signal import argrelextrema
import numpy as np

# Libraries needed for Kernel Density
from sklearn.neighbors import KernelDensity
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.dates import DateFormatter

# Libraries needed for DBSCAN
from sklearn.cluster import DBSCAN


class DBSCANClustering:

    @staticmethod
    def parse_time_str(str):
        if str[-1] not in ['s', 'm', 'h']:
            raise Exception('str should end with [s, m, h]')
        if str[-1] == 's':
            return int(str[:-1])
        elif str[-1] == 'm':
            return int(str[:-1]) * 60
        elif str[-1] == 'h':
            return int(str[:-1]) * 3600

    def __init__(self, eps):
        self.eps = DBSCANClustering.parse_time_str(eps)

    # Returns a list of clusters, where each cluster is a list of commits
    def run(self, commits: list[Commit]) -> list[list[Commit]]:
        commits_np = np.array(commits).reshape(-1, 1)
        unix_times = np.array([c.unix_time for c in commits]).reshape(-1, 1)
        dbscan = DBSCAN(eps=self.eps, min_samples=2).fit(X=unix_times)
        return [list(commits_np[np.where(np.equal(dbscan.labels_, i))][:, 0])
                for i in set(dbscan.labels_) if i != -1]

    # Returns the cluster ID for each commit
    def run_inverted(self, commits: list[Commit]) -> list[int]:
        unix_times = np.array([c.unix_time for c in commits]).reshape(-1, 1)
        dbscan = DBSCAN(eps=self.eps, min_samples=2).fit(X=unix_times)
        return list(cluster_id for cluster_id in dbscan.labels_ if cluster_id != -1)


# Based on Kernel Density Estimator, using min-max as breakpoints
class KDEClustering:
    def __init__(self, bandwidth: float, gran: int = 1000):
        self.bandwidth = bandwidth
        self.gran = gran
        self.ranges_x = None
        self.ranges_y = None
        self.unix_times = None
        self.min = None
        self.max = None
        self.clusters = []

    def run(self, commits: list[Commit]):
        self.unix_times = np.array([c.unix_time for c in commits]).reshape(-1, 1)
        commits_np = np.array(commits).reshape(-1, 1)
        x_vector = np.linspace(self.unix_times[0], self.unix_times[-1], self.gran)

        # Fit the data to KDE
        kde = KernelDensity(kernel='gaussian', bandwidth=self.bandwidth).fit(self.unix_times)
        e = kde.score_samples(x_vector.reshape(-1, 1))

        # Get min/max
        self.min, self.max = argrelextrema(e, np.less)[0], argrelextrema(e, np.greater)[0]
        self.__calc_cluster_ranges(x_vector, e, self.min)

        for range_x in self.ranges_x:
            cluster_x = np.where(
                np.logical_and(self.unix_times >= range_x[0], self.unix_times <= range_x[-1]))
            self.clusters.append(commits_np[cluster_x])
        return self.clusters

    def __calc_cluster_ranges(self, s, e, mi):
        self.ranges_x = [s[:mi[0] + 1]]
        self.ranges_y = [e[:mi[0] + 1]]
        for i in range(0, len(mi) - 1):
            self.ranges_x.append(s[mi[i]:mi[i + 1] + 1])
            self.ranges_y.append(e[mi[i]:mi[i + 1] + 1])
        self.ranges_x.append(s[mi[-1]:])
        self.ranges_y.append(e[mi[-1]:])

    def plot_density(self, window: int = 120):
        if self.ranges_x is None:
            print("Error! Please call run first")
            return

        fig, axs = plt.subplots(2)
        fig.suptitle('Density Graph')
        fig.subplots_adjust(left=0.25, bottom=0.25)

        time_left = self.unix_times[0][0]
        time_right = self.unix_times[-1][0]
        axis_position = plt.axes([0.2, 0.1, 0.65, 0.03],
                                 facecolor='White')
        slider_position = Slider(
            ax=axis_position, label='Time', valmin=time_left, valmax=time_right, valinit=time_left)

        colors = ['r', 'g', 'b']
        for i in range(0, len(self.ranges_y)):
            _x = [datetime.utcfromtimestamp(tm[0]) for tm in self.ranges_x[i]]
            _y = self.ranges_y[i]
            axs[0].plot_date(_x, _y, colors[i % 3])

        initial_window = [datetime.utcfromtimestamp(
            time_left), datetime.utcfromtimestamp(time_left + window)]

        axs[0].xaxis.set_major_formatter(DateFormatter('%d/%m %H:%M'))
        axs[1].xaxis.set_major_formatter(DateFormatter('%d/%m %H:%M'))

        axs[0].set_xlim(initial_window)
        axs[1].set_xlim(initial_window)

        axs[1].plot_date([datetime.utcfromtimestamp(tm[0]) for tm in self.unix_times], [
                         0]*len(self.unix_times), marker="o", markersize=5, markerfacecolor="red")

        def update(val):
            pos = slider_position.val
            axs[0].set_xlim([datetime.utcfromtimestamp(
                pos), datetime.utcfromtimestamp(pos + window)])
            axs[1].set_xlim([datetime.utcfromtimestamp(
                pos), datetime.utcfromtimestamp(pos + window)])
            fig.canvas.draw_idle()

        # update function called using on_changed() function
        slider_position.on_changed(update)

        plt.show()
