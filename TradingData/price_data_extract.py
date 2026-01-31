"""extract data to json files from excel"""
import copy

import pandas as pd
import json


def custom_normalize(series, p_max, p_min):
    return 1 - 2 * (p_max - series) / (p_max - p_min)


def process_price_data(file_path):
    """
    处理期货数据Excel文件，提取指定列并计算价格变化幅度

    参数:
    file_path (str): Excel文件路径

    返回:
    pandas.DataFrame: 处理后的数据
    """
    # 读取Excel文件的第一个sheet，跳过前两行（标题和单位行）
    df = pd.read_excel(file_path, header=0, skiprows=[0, 1, 2])

    # 选择需要的列
    selected_columns = ['Date', 'settle', 'high', 'low', 'pre_settle']
    df_selected = df[selected_columns]
    # df_selected['昨结算价'] = [0] * len(df_selected)
    # for i in range(1, len(df_selected)):
    #     df_selected['昨结算价'].iloc[i] = df_selected['结算价'].iloc[i-1]
    #
    # df_selected = df_selected[1:]
    # print(df_selected)

    # 重命名列以提高可读性
    df_selected.columns = ['交易日期', '日结算价', '日最高价', '日最低价', '昨结算价']

    # 计算价格变化幅度
    # 相对于昨结算价的变化百分比
    df_selected['日结算价变化率'] = (df_selected['日结算价'] - df_selected['昨结算价']) / df_selected['昨结算价']
    df_selected['日最高价变化率'] = (df_selected['日最高价'] - df_selected['昨结算价']) / df_selected['昨结算价']
    df_selected['日最低价变化率'] = (df_selected['日最低价'] - df_selected['昨结算价']) / df_selected['昨结算价']

    # 分别计算三列变化率的最大值和最小值
    p_max = max(
        df_selected['日结算价变化率'].max(),
        df_selected['日最高价变化率'].max(),
        df_selected['日最低价变化率'].max()
    )
    p_min = min(
        df_selected['日结算价变化率'].min(),
        df_selected['日最高价变化率'].min(),
        df_selected['日最低价变化率'].min()
    )

    # 对三列进行归一化
    df_selected['日结算价变化率_std'] = custom_normalize(df_selected['日结算价变化率'], p_max, p_min)
    df_selected['日最高价变化率_std'] = custom_normalize(df_selected['日最高价变化率'], p_max, p_min)
    df_selected['日最低价变化率_std'] = custom_normalize(df_selected['日最低价变化率'], p_max, p_min)

    returnList = []
    for c in [df_selected['日最低价变化率_std'], df_selected['日最高价变化率_std'], df_selected['日结算价变化率_std']]:
        for d in c.values:
            # print(d)
            returnList.append([d, 1])

    return returnList, p_max, p_min


def price_data_20_days(file_path, start_date):
    """
    统计自start_date开始的连续20个交易日的结算价和，一周，一个月涨跌幅
    返回：list[{"settle": [last five days settle], "week", "month"}]
    """
    # 读取Excel文件的第一个sheet，跳过前两行（标题和单位行）
    df = pd.read_excel(file_path, header=0, skiprows=[1, 2])

    # 选择需要的列
    selected_columns = ['Trddt', 'Stprc']
    df_selected = df[selected_columns]
    date_column = df_selected.columns[0]

    returnLst = []
    count = 0
    next_day = 0
    while True:
        # 获取日期索引
        next_date = pd.to_datetime(start_date) + pd.Timedelta(days=next_day)
        try:
            target_date_idx = df_selected[df_selected[date_column] == next_date.strftime('%Y-%m-%d')].index[0]
            prev_5s = df_selected.iloc[max(0, target_date_idx-5):target_date_idx, 1].tolist()
            prev_6 = df_selected.iloc[target_date_idx-6, 1]
            prev_20 = df_selected.iloc[target_date_idx-20, 1]
            tempDict = {
                "date": next_date.strftime('%Y-%m-%d'),
                "prev_5_settle": prev_5s,
                "week_difference": (prev_5s[-1] - prev_6) / prev_6,
                "month_difference": (prev_5s[-1] - prev_20) / prev_20
            }
            returnLst.append(tempDict)
            count += 1
            next_day += 1
            if count == 20:
                break
        except :
            next_day += 1

    return returnLst
