"""extract amount data to json files from excel"""
import copy

import numpy as np
import pandas as pd
import json

import pandas as pd


def custom_normalize_amount(series, a_max, a_min):
    """将交易额按照 group 分组，最大值最小值归一化"""
    return 1 - (a_max - series) / (a_max - a_min)


def extract_account_rank_data(file_path, sheet_name, target_date, target_ranktype):
    """
    从Excel文件中提取特定日期和排名类型的数据，并按名次排序

    参数:
    file_path (str): Excel文件的路径
    target_date (str): 目标日期，格式为 'YYYY-MM-DD'
    target_ranktype (int): 目标排名类型

    返回:
    pandas.DataFrame: 筛选和排序后的数据
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=0, skiprows=[1, 2])

        # 转换交易日期列为日期类型
        df['Trddt'] = pd.to_datetime(df['Trddt'])

        # 筛选数据：特定日期和排名类型
        filtered_df = df[
            (df['Trddt'].dt.strftime('%Y-%m-%d') == target_date) &
            (df['Ranktype'] == target_ranktype)
            ]

        # 按名次排序
        sorted_df = filtered_df.sort_values('Rank')

        # 选择需要的列
        result_df = sorted_df[['Trddt', 'Rank', 'Ashortnme']]

        return result_df

    except Exception as e:
        print(f"发生错误：{e}")
        return None

def analyze_futures_data(file_path, start_date, end_date, target_ranktype, analysis_column, customer_groups):
    """
    分析期货数据，按指定客户分组计算指定时间段和排名类型的数据汇总

    参数:
    file_path (str): Excel文件路径
    start_date (str): 开始日期 ('YYYY-MM-DD')
    end_date (str): 结束日期 ('YYYY-MM-DD')
    target_ranktype (int): 目标排名类型
    analysis_column (str): 需要分析的列名
    customer_groups (list): 客户分组列表

    返回:
    dict: 每个分组在每个交易日的数据汇总
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=0, skiprows=[1, 2])

        # 转换日期列
        df['Trddt'] = pd.to_datetime(df['Trddt'])

        # 筛选日期范围和排名类型
        filtered_df = df[
            (df['Trddt'] >= pd.to_datetime(start_date)) &
            (df['Trddt'] <= pd.to_datetime(end_date)) &
            (df['Ranktype'] == target_ranktype)
            ]

        # 初始化结果字典
        group_results = {}
        extreme_amounts = {'max': [], 'min': []} # 每个群组的最大，最小购买量

        # 遍历每个客户分组
        for i, group in enumerate(customer_groups, 0):
            # 筛选当前分组的数据
            group_df = filtered_df[filtered_df['Ashortnme'].isin(group)]

            # 按交易日期分组求和
            group_summary = group_df.groupby('Trddt')[analysis_column].sum().reset_index()
            # 计算极值信息
            extreme_amounts['max'].append(group_summary[analysis_column].max())
            extreme_amounts['min'].append(group_summary[analysis_column].min())

            # 存储结果
            group_results[f'Group {i}'] = group_summary

        return group_results, extreme_amounts

    except Exception as e:
        print(f"发生错误：{e}")
        return None

def get_last_day_futures_data(file_path, end_date, target_ranktype, analysis_column, customer_groups):
    """
    分析期货数据，按指定客户分组计算指定时间段和排名类型的数据汇总

    参数:
    file_path (str): Excel文件路径
    start_date (str): 开始日期 ('YYYY-MM-DD')
    end_date (str): 结束日期 ('YYYY-MM-DD')
    target_ranktype (int): 目标排名类型
    analysis_column (str): 需要分析的列名
    customer_groups (list): 客户分组列表

    返回:
    dict: 每个分组在每个交易日的数据汇总
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=0, skiprows=[1, 2])

        # 转换日期列
        df['Trddt'] = pd.to_datetime(df['Trddt'])

        # 筛选日期范围和排名类型
        filtered_df = df[
            (df['Trddt'] == pd.to_datetime(end_date)) &
            (df['Ranktype'] == target_ranktype)
            ]

        # 初始化结果字典
        group_results = {}

        # 遍历每个客户分组
        for i, group in enumerate(customer_groups, 0):
            # 筛选当前分组的数据
            group_df = filtered_df[filtered_df['Ashortnme'].isin(group)]

            # 按交易日期分组求和
            group_summary = group_df.groupby('Trddt')[analysis_column].sum().reset_index()

            # 存储结果
            group_results[f'group {i}'] = group_summary

        return group_results

    except Exception as e:
        print(f"发生错误：{e}")
        return None

if __name__ == '__main__':
    fileName = 'IH2412'
    file_path = f'{fileName}_Data0.xlsx'
    sheet_name = 'IH2412持仓排名数据'
    target_date = '2024-11-29'
    target_ranktype = 1

    # 提取数据
    result = extract_account_rank_data(file_path, sheet_name, target_date, target_ranktype)

    # 用户分组
    groups = [[1, 6, 7], [2, 4, 5], [3, 8, 9, 10], [11, 12, 13, 14, 15]]
    groups_names = [[], [], [], []]


    print(result)
    # 将用户分组对应至客户简称
    if result is not None:
        for i in range(15):
            for j in range(len(groups)):
                if i in groups[j]:
                    groups_names[j].append(result['Ashortnme'].iloc[i])
    print(groups_names)


    # 按日期统计分组交易量
    # 起止日期
    start_date = '2024-10-20'
    end_date = '2024-11-22'

    # long
    group_results_long, extreme_amounts_long = analyze_futures_data(
        file_path,
        start_date,
        end_date,
        target_ranktype=4,
        analysis_column='Lgpstin',
        customer_groups=groups_names
    )

    # before_long, before_before_long
    before_long = get_last_day_futures_data(
        file_path,
        end_date,
        target_ranktype=4,
        analysis_column='Lgpstin',
        customer_groups=groups_names
    )

    before_before_long = get_last_day_futures_data(
        file_path,
        end_date,
        target_ranktype=1,
        analysis_column='Lgpst',
        customer_groups=groups_names
    )

    # short
    group_results_short, extreme_amounts_short = analyze_futures_data(
        file_path,
        start_date,
        end_date,
        target_ranktype=7,
        analysis_column='Shpstin',
        customer_groups=groups_names
    )

    # before_short, before_before_short
    before_short = get_last_day_futures_data(
        file_path,
        end_date,
        target_ranktype=7,
        analysis_column='Shpstin',
        customer_groups=groups_names
    )

    before_before_short = get_last_day_futures_data(
        file_path,
        end_date,
        target_ranktype=2,
        analysis_column='Shpst',
        customer_groups=groups_names
    )

    for i in range(len(groups_names)):
        bl, bbl = before_long[f'group {i}'].iloc[0][-1], before_before_long[f'group {i}'].iloc[0][-1]
        bs, bbs = before_short[f'group {i}'].iloc[0][-1], before_before_short[f'group {i}'].iloc[0][-1]
        print(f'group {i}: [{0.6*bl}, {0.4*bl}], [{0.6*(bbl-bl)}, {0.4*(bbl-bl)}], '
              f'[{0.6*bs}, {0.4*bs}], [{0.6*(bbs-bs)}, {0.4*(bbs-bs)}]')

    # print(group_results_long)
    # print(group_results_short)

    # 导出
    longs = []
    shorts = []
    for i in range(len(groups_names)):
        dl, ds = list(group_results_long[f'Group {i}']['Lgpstin']), list(group_results_short[f'Group {i}']['Shpstin'])
        max_i_long, min_i_long = extreme_amounts_long['max'][i], extreme_amounts_long['min'][i]
        max_i_short, min_i_short = extreme_amounts_short['max'][i], extreme_amounts_short['min'][i]
        dl = list(custom_normalize_amount(np.array(dl), max_i_long, min_i_long))
        ds = list(custom_normalize_amount(np.array(ds), max_i_short, min_i_short))
        temp = []
        for j in dl:
            temp.append([j, 1])
        longs.append(copy.deepcopy(temp))
        temp.clear()
        for j in ds:
            temp.append([j, -1])
        shorts.append(copy.deepcopy(temp))
    extract_amount_data = {
        'groups_names': groups_names,
        'start_date': start_date,
        'end_date': end_date,
        'extreme_long': extreme_amounts_long,
        'extreme_short': extreme_amounts_short,
        'long': longs,
        'short': shorts
    }
    # print(extract_amount_data)
    with open(f'{fileName}_amount.json', 'w', encoding='utf-8') as f :
        json.dump(extract_amount_data, f, indent=4, ensure_ascii=False)
