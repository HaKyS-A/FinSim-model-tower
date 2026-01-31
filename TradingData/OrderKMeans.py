"""基于市场行情数据实现行为的6-均值聚类，单日最高价、最低价、均价、交易量"""
import numpy as np
import matplotlib.pyplot as plt
import json

OrderPriceLst = ['大差价+', '大差价-', '中差价+', '中差价-', '小差价+', '小差价-', '现价0']
OrderAmountLst = ['大量+', '大量-', '中量+', '中量-', '少量+', '少量-']


class OrderKMeansPrice:
    def __init__(self, initial_centers=None):
        """

        初始化6-均值聚类算法

        参数:
        initial_centers: 初始聚类中心，默认为特定的金融交易模式
        """
        if initial_centers is None:
            # 预定义的5个初始聚类中心
            self.centers = np.array([
                # 大差价+
                [0.8, 1],
                # 大差价-
                [-0.8, 1],
                # 中差价+
                [0.3, 1],
                # 中差价-
                [-0.3, 1],
                # 小差价+
                [0.1, 1],
                # 小差价-
                [-0.1, 1],
                # 现价0
                [0, 1]
            ])
        else:
            self.centers = np.array(initial_centers)

        self.clusters = None

    def _euclidean_distance(self, point1, point2):
        """
        计算欧几里得距离

        参数:
        point1: 第一个点
        point2: 第二个点

        返回:
        两点间的距离
        """
        return np.sqrt(np.sum((point1 - point2) ** 2))

    def _assign_clusters(self, data):
        """
        将数据点分配到最近的聚类中心

        参数:
        data: 归一化的数据点列表

        返回:
        每个数据点的聚类标签
        """
        cluster_labels = []
        for point in data:
            # 计算点到每个中心的距离
            distances = [self._euclidean_distance(point, center) for center in self.centers]
            # 分配到最近的中心
            cluster_labels.append(np.argmin(distances))
        return np.array(cluster_labels)

    def _update_centers(self, data, cluster_labels):
        """
        根据聚类重新计算聚类中心

        参数:
        data: 归一化的数据点列表
        cluster_labels: 每个点的聚类标签

        返回:
        更新后的聚类中心
        """
        new_centers = []
        for i in range(len(self.centers)):
            # 找出属于该聚类的所有点
            cluster_points = data[cluster_labels == i]

            if len(cluster_points) > 0:
                # 计算新的聚类中心（均值）
                new_center = np.mean(cluster_points, axis=0)
                new_centers.append(new_center)
            else:
                # 如果某个聚类没有点，保持原中心
                new_centers.append(self.centers[i])

        return np.array(new_centers)

    def fit(self, data, max_iterations=100, tolerance=1e-4):
        """
        执行K-means聚类算法

        参数:
        data: 归一化的数据点列表
        max_iterations: 最大迭代次数
        tolerance: 聚类中心变化的容忍度

        返回:
        聚类结果
        """
        data = np.array(data)

        for _ in range(max_iterations):
            # 保存旧的聚类中心
            old_centers = self.centers.copy()

            # 分配数据点到聚类
            self.clusters = self._assign_clusters(data)

            # 更新聚类中心
            self.centers = self._update_centers(data, self.clusters)

            # 检查是否收敛
            if np.all(np.abs(self.centers - old_centers) < tolerance):
                break

        return self.clusters

    def predict(self, point):
        """
        预测新点的聚类

        参数:
        point: 待预测的归一化数据点

        返回:
        预测的聚类标签
        """
        distances = [self._euclidean_distance(point, center) for center in self.centers]
        return np.argmin(distances)

    def get_centers(self):
        """
        获取最终的聚类中心

        返回:
        聚类中心列表
        """
        return self.centers

    def visualize_clusters(self, data, labels=None, title='Clustering Visualization'):
        """
        可视化聚类结果

        参数:
        data: 原始数据点
        labels: 聚类标签（可选）
        title: 图表标题
        """
        # 如果没有提供标签，使用已有的聚类结果
        if labels is None:
            if self.clusters is None:
                raise ValueError("请先执行fit()方法或提供聚类标签")
            labels = self.clusters

        # 转换为numpy数组
        data = np.array(data)
        labels = np.array(labels)

        # 创建颜色映射
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown', 'pink']

        # 创建图形
        plt.figure(figsize=(10, 6))

        # 绘制每个聚类
        # print(data, labels)
        for i in range(len(self.centers)):
            # 找出属于该聚类的点
            cluster_points = data[labels == i]

            # 如果该聚类有点
            if len(cluster_points) > 0:
                plt.scatter(cluster_points[:, 0], cluster_points[:, 1],
                            c=colors[i], label=f'Cluster {i}', alpha=0.7)

        # 绘制聚类中心
        plt.scatter(self.centers[:, 0], self.centers[:, 1],
                    c='black', marker='x', s=200, linewidths=3, label='Centroids')

        # 设置图表细节
        plt.title(title)
        plt.xlabel('price')
        plt.ylabel('buy/sale')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)

        # 显示图表
        plt.tight_layout()
        plt.show()

    def cluster_price_statistics(self, data):
        """
        给出每个类的价格统计数据
        :param data: 列表形式全部数据
        :return: list[tuple[avg, std]]
        """
        data_array = np.array(data)
        clusters = np.array(self.clusters)
        returnLst = []
        for i in range(len(self.centers)):
            # 找出属于该聚类的点
            cluster_points = data_array[clusters == i]
            print('\n-----------')
            print(OrderPriceLst[i], ':')
            avg = np.average(cluster_points[:, 0])
            std = np.std(cluster_points[:, 0])
            print('均价：', avg)
            print('标准差：', std)
            returnLst.append((avg, std))

        return returnLst


class OrderKMeansAmount:
    def __init__(self, initial_centers=None):
        """

        初始化6-均值聚类算法

        参数:
        initial_centers: 初始聚类中心，默认为特定的金融交易模式
        """
        if initial_centers is None:
            # 预定义的6个初始聚类中心
            self.centers = np.array([
                # 大量买
                [0.8, 1],
                # 大量卖
                [0.8, -1],
                # 中量买
                [0.4, 1],
                # 中量卖
                [0.4, -1],
                # 少量买
                [0, 1],
                # 少量卖
                [0, -1]
            ])
        else:
            self.centers = np.array(initial_centers)

        self.clusters = None

    def _euclidean_distance(self, point1, point2):
        """
        计算欧几里得距离

        参数:
        point1: 第一个点
        point2: 第二个点

        返回:
        两点间的距离
        """
        return np.sqrt(np.sum((point1 - point2) ** 2))

    def _assign_clusters(self, data):
        """
        将数据点分配到最近的聚类中心

        参数:
        data: 归一化的数据点列表

        返回:
        每个数据点的聚类标签
        """
        cluster_labels = []
        for point in data:
            # 计算点到每个中心的距离
            distances = [self._euclidean_distance(point, center) for center in self.centers]
            # 分配到最近的中心
            cluster_labels.append(np.argmin(distances))
        return np.array(cluster_labels)

    def _update_centers(self, data, cluster_labels):
        """
        根据聚类重新计算聚类中心

        参数:
        data: 归一化的数据点列表
        cluster_labels: 每个点的聚类标签

        返回:
        更新后的聚类中心
        """
        new_centers = []
        for i in range(len(self.centers)):
            # 找出属于该聚类的所有点
            cluster_points = data[cluster_labels == i]

            if len(cluster_points) > 0:
                # 计算新的聚类中心（均值）
                new_center = np.mean(cluster_points, axis=0)
                new_centers.append(new_center)
            else:
                # 如果某个聚类没有点，保持原中心
                new_centers.append(self.centers[i])

        return np.array(new_centers)

    def fit(self, data, max_iterations=100, tolerance=1e-4):
        """
        执行K-means聚类算法

        参数:
        data: 归一化的数据点列表
        max_iterations: 最大迭代次数
        tolerance: 聚类中心变化的容忍度

        返回:
        聚类结果
        """
        data = np.array(data)

        for _ in range(max_iterations):
            # 保存旧的聚类中心
            old_centers = self.centers.copy()

            # 分配数据点到聚类
            self.clusters = self._assign_clusters(data)

            # 更新聚类中心
            self.centers = self._update_centers(data, self.clusters)

            # 检查是否收敛
            if np.all(np.abs(self.centers - old_centers) < tolerance):
                break

        return self.clusters

    def predict(self, point):
        """
        预测新点的聚类

        参数:
        point: 待预测的归一化数据点

        返回:
        预测的聚类标签
        """
        distances = [self._euclidean_distance(point, center) for center in self.centers]
        return np.argmin(distances)

    def get_centers(self):
        """
        获取最终的聚类中心

        返回:
        聚类中心列表
        """
        return self.centers

    def visualize_clusters(self, data, labels=None, title='Clustering Visualization'):
        """
        可视化聚类结果

        参数:
        data: 原始数据点
        labels: 聚类标签（可选）
        title: 图表标题
        """
        # 如果没有提供标签，使用已有的聚类结果
        if labels is None:
            if self.clusters is None:
                raise ValueError("请先执行fit()方法或提供聚类标签")
            labels = self.clusters

        # 转换为numpy数组
        data = np.array(data)
        labels = np.array(labels)

        # 创建颜色映射
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown']

        # 创建图形
        plt.figure(figsize=(10, 6))

        # 绘制每个聚类
        # print(data, labels)
        for i in range(len(self.centers)):
            # 找出属于该聚类的点
            cluster_points = data[labels == i]

            # 如果该聚类有点
            if len(cluster_points) > 0:
                plt.scatter(cluster_points[:, 0], cluster_points[:, 1],
                            c=colors[i], label=f'Cluster {i}', alpha=0.7)

        # 绘制聚类中心
        plt.scatter(self.centers[:, 0], self.centers[:, 1],
                    c='black', marker='x', s=200, linewidths=3, label='Centroids')

        # 设置图表细节
        plt.title(title)
        plt.xlabel('price')
        plt.ylabel('buy/sale')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)

        # 显示图表
        plt.tight_layout()
        plt.show()

    def cluster_amount_statistics(self, data):
        """
        给出每个类的价格统计数据
        :param data: 列表形式全部数据
        :return: list[tuple[avg, std]]
        """
        data_array = np.array(data)
        clusters = np.array(self.clusters)
        returnLst = []
        for i in range(len(self.centers)):
            # 找出属于该聚类的点
            cluster_points = data_array[clusters == i]
            print('\n-----------')
            print(OrderAmountLst[i], ':')
            avg = np.average(cluster_points[:, 0])
            std = np.std(cluster_points[:, 0])
            longOrShort = cluster_points[0, 1]
            print('均量：', avg)
            print('标准差：', std)
            print('多/空：', longOrShort)
            returnLst.append((avg, std, longOrShort))

        return returnLst


# 使用示例
if __name__ == "__main__":
    # 输入文件前缀
    fileName = 'IH2412'
    with open(f'{fileName}_price.json', 'r', encoding='utf-8') as f:
        sample_data = json.load(f)

    # 创建聚类器
    kmeans = OrderKMeansPrice()

    # 拟合数据
    clusters = kmeans.fit(sample_data['data'], max_iterations=20)

    # 打印结果
    print("聚类标签:", clusters)
    print("最终聚类中心:", kmeans.get_centers())
    kmeans.visualize_clusters(sample_data['data'])
    statistics = kmeans.cluster_price_statistics(sample_data['data'])

    p_max = sample_data['p_max']
    p_min = sample_data['p_min']

    # 输出处理后的价格生成器数据，包括 :
    # {'p_max': p_max # 最大涨幅, 'p_min': p_min # 最大跌幅, 'statistics': statistics # 归一化均值与标准差}
    with open(f'{fileName}_price_generator.json', 'w', encoding='utf-8') as f:
        json.dump({'p_max': p_max, 'p_min': p_min, 'statistics': statistics}, f, indent=4)



    # # amount
    # with open(f'{fileName}_amount.json', 'r', encoding='utf-8') as f:
    #     amount_data = json.load(f)
    #
    # amountReturnDict = {
    #     'avg_std_order': ['大量', '中量', '少量'],
    #     'long': {'max': [], 'min':[], 'avg&std': []},
    #     'short': {'max': [], 'min':[], 'avg&std':[]}
    # }
    # # index - group_id - agent_id
    #
    # kmeans_amount = OrderKMeansAmount()
    #
    # # 遍历
    # for i in range(len(amount_data['groups_names'])):
    #     # long
    #     kmeans_amount = OrderKMeansAmount()
    #     max_long_i = amount_data['extreme_long']['max'][i]
    #     min_long_i = amount_data['extreme_long']['min'][i]
    #     amountReturnDict['long']['max'].append(max_long_i)
    #     amountReturnDict['long']['min'].append(min_long_i)
    #     data = amount_data['long'][i]
    #     # short
    #     max_short_i = amount_data['extreme_short']['max'][i]
    #     min_short_i = amount_data['extreme_short']['min'][i]
    #     amountReturnDict['short']['max'].append(max_short_i)
    #     amountReturnDict['short']['min'].append(min_short_i)
    #     data.extend(amount_data['short'][i])
    #
    #     # 拟合数据
    #     clusters = kmeans_amount.fit(data, max_iterations=20)
    #
    #     # 打印结果
    #     print(f"group {i}  聚类标签:", clusters)
    #     print(f"group {i}  最终聚类中心:", kmeans_amount.get_centers())
    #     kmeans_amount.visualize_clusters(data)
    #     statistics = kmeans_amount.cluster_amount_statistics(data)
    #     temp_long, temp_short = [], []
    #     for t in statistics:
    #         if t[2] == 1:
    #             temp_long.append((t[0], t[1]))
    #         else:
    #             temp_short.append((t[0], t[1]))
    #     amountReturnDict['long']['avg&std'].append(temp_long)
    #     amountReturnDict['short']['avg&std'].append(temp_short)
    #
    # print(amountReturnDict)
    #
    # with open(f'{fileName}_amount_generator.json', 'w', encoding='utf-8') as f:
    #     json.dump(amountReturnDict, f, ensure_ascii=False, indent=4)


