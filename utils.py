"""simulator.py 中使用到的小组件"""
import json
import os, copy
import random

import numpy as np
import torch.cuda

from Agent.players import QingShanPlayer, GlencorePlayer, OrdinaryPlayers

# 获取当前主程序的路径
current_path = os.path.dirname(os.path.abspath(__file__))

# 智能体路径
agent_folder = os.path.join(current_path, 'Agent')
# profiles
profile_folder = os.path.join(agent_folder, 'profiles')
# configs
config_folder = os.path.join(agent_folder, 'configs')


def agents_init(mode='LME',num=3):
    """
    初始化所有智能体
    :return: 一个智能体组成的列表
    """
    if mode == 'LME':
        QS = QingShanPlayer(
            profile_file=os.path.join(profile_folder, 'QingShanProfile0.txt'),
            config_file=os.path.join(config_folder, 'QingShanConfig.json')
        )
        GLE = GlencorePlayer(
            profile_file=os.path.join(profile_folder, 'GlencoreProfile0.txt'),
            config_file=os.path.join(config_folder, 'GlencoreConfig.json')
        )
        OPs = []
        for i in range(8):
            config_file = os.path.join(config_folder, f'OrdinaryConfig{i}.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                profile_name = json.load(f)['name']
                profile_file=os.path.join(profile_folder, f'{profile_name}.txt')
            OPs.append(
                OrdinaryPlayers(
                    profile_file=profile_file,
                    config_file=config_file
                )
            )

        returnList = [
            QS,
            GLE
        ]

        returnList.extend(OPs)

        return returnList
    elif mode == 'HET': #异质性 3/5/7/10个智能体
        QS = QingShanPlayer(
            profile_file=os.path.join(profile_folder, 'QingShanProfile0.txt'),
            config_file=os.path.join(config_folder, 'QingShanConfig.json')
        )
        GLE = GlencorePlayer(
            profile_file=os.path.join(profile_folder, 'GlencoreProfile0.txt'),
            config_file=os.path.join(config_folder, 'GlencoreConfig.json')
        )
        OPs = []
        if num==3:
            #3个智能体：青山，嘉能可，整合智能体
            config_file = os.path.join(config_folder, f'HET({num})' ,f'HET({num})Config.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                profile_name = json.load(f)['name']
                profile_file=os.path.join(profile_folder, f'{profile_name}.txt')
            OPs.append(
                OrdinaryPlayers(
                    profile_file=profile_file,
                    config_file=config_file
                )
            )
        elif num==5:#5个智能体：青山，嘉能可，InstitutionalProfile+ConservatismProfile，AggressiveProfile+NickelBuyer，ConservatismProfile
            for i in range(3):
                config_file = os.path.join(config_folder, f'HET({num})' , f'HET({num})Config{i}.json')
                with open(config_file, 'r', encoding='utf-8') as f:
                    profile_name = json.load(f)['name']
                    profile_file=os.path.join(profile_folder, f'{profile_name}.txt')
                OPs.append(
                    OrdinaryPlayers(
                        profile_file=profile_file,
                        config_file=config_file
                    )
                )
        elif num==7:#7个智能体：青山，嘉能可，InstitutionalProfile，AggressiveProfile，NickelBuyer，ConservatismProfile，ContrarianProfile
            for i in range(5):
                config_file = os.path.join(config_folder, f'HET({num})' ,f'HET({num})Config{i}.json')
                with open(config_file, 'r', encoding='utf-8') as f:
                    profile_name = json.load(f)['name']
                    profile_file=os.path.join(profile_folder, f'{profile_name}.txt')
                OPs.append(
                    OrdinaryPlayers(
                        profile_file=profile_file,
                        config_file=config_file
                    )
                )
        elif num==12: #12个智能体，在LME的基础上增加InstitutionalProfile2，ConservatismProfile2
            for i in range(10):
                config_file = os.path.join(config_folder, f'HET({num})' ,f'HET({num})Config{i}.json')
                with open(config_file, 'r', encoding='utf-8') as f:
                    profile_name = json.load(f)['name']
                    profile_file=os.path.join(profile_folder, f'{profile_name}.txt')
                OPs.append(
                    OrdinaryPlayers(
                        profile_file=profile_file,
                        config_file=config_file
                    )
                )
        returnList = [
            QS,
            GLE
        ]

        returnList.extend(OPs)

        return returnList
    elif mode == 'IH2412':
        OPs = []
        for i in range(8):
            config_file = os.path.join(config_folder, f'OrdinaryConfig{i}.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                profile_name = json.load(f)['name']
                profile_file = os.path.join(profile_folder, f'{profile_name}.txt')
            OPs.append(
                OrdinaryPlayers(
                    profile_file=profile_file,
                    config_file=config_file
                )
            )
    elif mode == 'TA501':
        OPs = []
        for i in range(8):
            config_file = os.path.join(config_folder, f'OrdinaryConfig{i}.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                profile_name = json.load(f)['name']
                profile_file = os.path.join(profile_folder, f'{profile_name}.txt')
            OPs.append(
                OrdinaryPlayers(
                    profile_file=profile_file,
                    config_file=config_file
                )
            )

        return OPs
    elif mode == 'SC2501':
        OPs = []
        for i in range(8):
            config_file = os.path.join(config_folder, f'OrdinaryConfig{i}.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                profile_name = json.load(f)['name']
                profile_file = os.path.join(profile_folder, f'{profile_name}.txt')
            OPs.append(
                OrdinaryPlayers(
                    profile_file=profile_file,
                    config_file=config_file
                )
            )

        return OPs
    elif mode == 'GCG2502':
        OPs = []
        for i in range(8):
            config_file = os.path.join(config_folder, f'OrdinaryConfig{i}.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                profile_name = json.load(f)['name']
                profile_file = os.path.join(profile_folder, f'{profile_name}.txt')
            OPs.append(
                OrdinaryPlayers(
                    profile_file=profile_file,
                    config_file=config_file
                )
            )

        return OPs
    elif mode == 'CH2503':
        OPs = []
        for i in range(8):
            config_file = os.path.join(config_folder, f'OrdinaryConfig{i}.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                profile_name = json.load(f)['name']
                profile_file = os.path.join(profile_folder, f'{profile_name}.txt')
            OPs.append(
                OrdinaryPlayers(
                    profile_file=profile_file,
                    config_file=config_file
                )
            )

        return OPs
    elif mode == 'SF2503':
        OPs = []
        for i in range(8):
            config_file = os.path.join(config_folder, f'OrdinaryConfig{i}.json')
            with open(config_file, 'r', encoding='utf-8') as f:
                profile_name = json.load(f)['name']
                profile_file = os.path.join(profile_folder, f'{profile_name}.txt')
            OPs.append(
                OrdinaryPlayers(
                    profile_file=profile_file,
                    config_file=config_file
                )
            )

        return OPs


def generate_transactions(transaction_request, account_info, agent_id, market_info, current_turn, security_fund_rate, limit, votality=True):
    """
    生成交易请求
    :param transaction_request: {"type", "amount", "price"}
    :param account_info: 账户信息
    :param agent_id: 智能体 ID
    :param market_info: 市场信息，提供价格
    :param current_turn: 轮次信息
    :return: list - [用户ID，下单轮次，订单类型（请将买入卖出换成buy和sell)，买入/卖出量（请给数据），单位价格（请给数据）]
    """
    returnList = []
    # 账户与市场信息
    available_deposit = float(account_info["available_deposit"])
    Ni_price = float(market_info["current_Ni_price"])

    for _ in range(10):
        # 随机生成10个订单
        type_order = "buy"
        if transaction_request["type"] == "卖出":
            type_order = "sell"
        ## 根据高斯分布生成价格
        price_miu, price_delta = Ni_price, 1.6
        rate = limit + 1
        p = transaction_request["price"]
        while abs(rate) > limit:
            if p == "当前价格":
                rate = 0.0
            elif p == "略高价格":
                rate = limit*0.1
            elif p == "略低价格":
                rate = -1*limit*0.1
            elif p == "更高价格":
                rate = limit*0.4
            elif p == "更低价格":
                rate = -1*limit*0.4
            elif p == "极高价格":
                rate = limit*0.8
            elif p == "极低价格":
                rate = -1*limit*0.8

            if abs(rate) > 15:
                price_delta = abs(rate) * 0.15
            if abs(rate) > 50:
                price_delta = abs(rate) * 0.1

            rate = np.random.normal(rate, price_delta)


        # 10% 的概率，订单类型变更，买->卖，价格提升 5%；卖->买，价格降低5%
        if votality:
            # 豁免，青山，嘉能可
            p = random.random()
            if p > 0.9:
                if type_order == 'buy':
                    type_order = 'sell'
                    rate += 5
                else:
                    type_order = 'buy'
                    rate -= 5


        price = price_miu * (1+rate/100.0)

        ## 根据高斯分布生成数量
        amount_max, amount_delta = ((available_deposit * 100 / security_fund_rate) / price) / 10, 10
        portion = -1
        a = transaction_request["amount"]
        while portion <= 0 or portion > 100:
            if a == "少量":
                portion = 25.0
            elif a == "半仓":
                portion = 50.0
            elif a == "大量":
                portion = 75.0
            elif a == "全仓":
                portion = 100.0
            portion = np.random.normal(portion, amount_delta)

        amount = amount_max * portion / 100.0


        returnList.append([agent_id, current_turn, type_order, amount, price])

    return returnList


# ablation study
def generate_transactions_without_generator(transaction_request, account_info, agent_id, market_info, current_turn, security_fund_rate, limit):
    """
    生成交易请求，无生成器模式，amount，price均为百分比小数
    :param transaction_request: {"type", "amount", "price"}
    :param account_info: 账户信息
    :param agent_id: 智能体 ID
    :param market_info: 市场信息，提供价格
    :param current_turn: 轮次信息
    :return: list - [用户ID，下单轮次，订单类型（请将买入卖出换成buy和sell)，买入/卖出量（请给数据），单位价格（请给数据）]
    """
    returnList = []
    # 账户与市场信息
    available_deposit = float(account_info["available_deposit"])
    Ni_price = float(market_info["current_Ni_price"])

    # 随机生成10个订单
    type = "buy"
    if transaction_request["type"] == "卖出":
        type = "sell"
    for i in range(10):
        ## 根据高斯分布生成价格
        price_miu = Ni_price
        p = transaction_request["price"]

        price = price_miu * (1+p*limit/10000.0)

        ## 根据高斯分布生成数量
        amount_max = (available_deposit / price) / 10
        a = transaction_request["amount"]

        amount = amount_max * a / 100.0

        returnList.append([agent_id, current_turn, type, amount, price])

    return returnList


def transactions_response_filter(succeeded, failed, agent_id):
    """
    根据用户 ID 筛选经过撮合后成功和失败的请求，返回两个子列表
    :param succeeded: 所有撮合成功的请求
    :param failed: 所有撮合失败的请求
    :param agent_id: 待检索的用户 id
    :return: (succeeded_filtered, failed_filtered) - 成功与失败的海选后的二元组
    """
    succeeded_filtered = []
    failed_filtered = []
    for response in succeeded:
        if response[0] == agent_id:
            succeeded_filtered.append(response)
    for response in failed:
        if response[0] == agent_id:
            failed_filtered.append(response)

    return succeeded_filtered, failed_filtered


def custom_normalize_price_reverse(series, p_max, p_min):
    return p_max - (1-series) * (p_max - p_min) / 2


def custom_normalize_amount_reverse(series, p_max, p_min):
    return p_max - (1-series) * (p_max - p_min)


def generate_transactions_new(price_file, amount_file, transaction_request, account_info, agent_id, market_info, current_turn, security_fund_rate, limit, votality=True):
    """
    生成交易请求，新增利用聚类得到的参数进行订单生产
    :param transaction_request: {"type", "amount", "price"}
    :param account_info: 账户信息
    :param agent_id: 智能体 ID
    :param market_info: 市场信息，提供价格
    :param current_turn: 轮次信息
    :return: list - [用户ID，下单轮次，订单类型（请将买入卖出换成buy和sell)，买入/卖出量（请给数据），单位价格（请给数据）]
    """
    returnList = []
    # 账户与市场信息
    Ni_price = float(market_info["current_Ni_price"])
    # specialized generator
    with open(price_file, 'r', encoding='utf-8') as f:
        price_parameters = json.load(f)
        # {'p_max': p_max # 最大涨幅, 'p_min': p_min # 最大跌幅, 'statistics': statistics # 归一化均值与标准差}

    with open(amount_file, 'r', encoding='utf-8') as f:
        amount_parameters = json.load(f)
        # amountReturnDict = {
        #     'avg_std_order': ['大量', '中量', '少量'],
        #     'long': {'max': [], 'min':[], 'avg&std': []},
        #     'short': {'max': [], 'min':[], 'avg&std':[]}
        # }
        # index - group_id - agent_id

    # 随机生成10个订单
    for i in range(20):
        type_order = "buy"
        if transaction_request["type"] == "卖出":
            type_order = "sell"
        ## 根据高斯分布生成价格
        rate = limit + 1
        p = transaction_request["price"]
        while abs(rate) > limit/100:
            j = -1
            if p == "当前价格":
                j = 6
            elif p == "略高价格":
                j = 4
            elif p == "略低价格":
                j = 5
            elif p == "更高价格":
                j = 2
            elif p == "更低价格":
                j = 3
            elif p == "极高价格":
                j = 0
            elif p == "极低价格":
                j = 1

            price_miu, price_delta = price_parameters['statistics'][j][0], price_parameters['statistics'][j][1]

            rate = np.random.normal(price_miu, price_delta)
            rate = custom_normalize_price_reverse(rate, price_parameters['p_max'], price_parameters['p_min'])

            # print(rate)

        # 15% 的概率，订单类型变更，买->卖，价格提升 0.2%；卖->买，价格降低0.2%
        if votality:
            # 豁免，青山，嘉能可
            po = random.random()
            if po > 0.75:
                if type_order == 'buy':
                    type_order = 'sell'
                    rate += 0.000
                else:
                    type_order = 'buy'
                    rate -= 0.000

            # if p == "略高价格":
            #     rate += 0.015
            # elif p == "略低价格":
            #     rate -= 0.015

        price = Ni_price * (1+rate)

        ## 根据高斯分布生成数量
        amount = -1
        a = transaction_request["amount"]
        ## 半仓与大量都偏常规交易水平
        while amount < 0:
            j = -1
            if a == "少量":
                j = 2
            elif a == "半仓":
                j = 1
            elif a == "大量":
                j = 0
            elif a == "全仓":
                j = 0

            k = agent_id // 2    # 用户所属 group
            if type_order == 'buy':
                amount_miu, amount_std = amount_parameters['long']['avg&std'][k][j][0], amount_parameters['long']['avg&std'][k][j][1]
                amount = np.random.normal(amount_miu, amount_std)
                amount = custom_normalize_amount_reverse(
                    amount,
                    amount_parameters['long']['max'][k],
                    amount_parameters['long']['min'][k]
                ) / 30   # /30 均摊至每个回合的交易区间、代表一日
            elif type_order == 'sell':
                amount_miu, amount_std = amount_parameters['short']['avg&std'][k][j][0], amount_parameters['short']['avg&std'][k][j][1]
                amount = np.random.normal(amount_miu, amount_std)
                amount = custom_normalize_amount_reverse(
                    amount,
                    amount_parameters['short']['max'][k],
                    amount_parameters['short']['min'][k]
                ) / 30

            # print(amount)

        returnList.append([agent_id, current_turn, type_order, amount, price])

    return returnList


def filtered_transactions_formatter(succeeded, failed):
    """
    将成功的，和失败的交易有n元组转化为一个字符串，用于提示词输入
    :param succeeded: 筛选后的成功请求列表
    :param failed: 晒窜后的失败请求列表
    :return: 一个字符串
    """
    # 处理成功交易
    total_volume = 0.0
    weighted_sum = 0.0
    for t in succeeded:
        volume, price = t[3], t[4]
        total_volume += float(volume)
        weighted_sum += float(volume) * float(price)

    if total_volume > 0:
        avg_price = weighted_sum / total_volume
        success_summary = f"成功交易: 总成交量 = {total_volume} 手, 加权平均成交价格 = {avg_price:.4f} 元/手"
    else:
        success_summary = "成功交易: 无"

    # 处理失败交易
    total_failed_volume = 0.0
    weighted_failed_sum = 0.0
    for t in failed:
        volume, price = t[3], t[4]
        total_failed_volume += float(volume)
        weighted_failed_sum += float(volume) * float(price)

    if total_failed_volume > 0:
        avg_failed_price = weighted_failed_sum / total_failed_volume
        failed_summary = f"未成交: 总未成交量 = {total_failed_volume} 手, 加权平均请求价格 = {avg_failed_price:.4f} 元/手"
    else:
        failed_summary = "未成交: 无"

    return f"{success_summary};\n {failed_summary}"


def update_requests_after_withdraw(failed_filtered, withdraw_requests):
    """
    撤单发起后，从请求列表中删除成功撮合的请求
    :param failed_filtered: 当前用户所有撮合失败的所有请求
    :param withdraw_requests: 撤单请求
    :return: 新的 all_requests，仅含有 order_id, list[int]
    """
    amount = withdraw_requests["withdrawal"]
    p = 0.0
    if amount == "不撤单":
        p = 0.0
    elif amount == "少量":
        p = 0.25
    elif amount == "一半":
        p = 0.5
    elif amount == "大量":
        p = 0.75
    elif amount == "全部":
        p = 1.0

    remained_requests = [r[1] for r in failed_filtered if random.random() > (1-p)]
    return remained_requests


# ablation study
def update_requests_after_withdraw_without_generator(failed_filtered, withdraw_requests):
    """
    撤单发起后，从请求列表中删除成功撮合的请求，无生成器模式，withdrawal 为百分比小数
    :param failed_filtered: 当前用户所有撮合失败的所有请求
    :param withdraw_requests: 撤单请求
    :return: 新的 all_requests，仅含有 order_id, list[int]
    """
    p = withdraw_requests["withdrawal"] / 100.0

    remained_requests = [r[1] for r in failed_filtered if random.random() > (1-p)]
    return remained_requests


def news_delay(news: tuple[str, str], p=0.1):
    """
    模拟消息延迟，以 p(default 0.1) 的概率收到上一轮的新闻
    :param news: （上一回合新闻，本回合新闻）
    :param p: 延迟概率
    :return: str 返回的新闻
    """
    if random.random() > p:
        return news[-1]
    else:
        return news[0]
