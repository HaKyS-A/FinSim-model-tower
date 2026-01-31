"""主程序，初始化游戏设定，玩家和引擎"""
import json
import time
import torch
import argparse

try:
    from Engine.engine import Engine
except:
    from .Engine.engine import Engine
from simulator import Simulator
from news_init_config_updator import *
from utils import agents_init
import os

# 获取当前主程序的路径
current_path = os.path.dirname(os.path.abspath(__file__))

# 智能体路径
agent_folder = os.path.join(current_path, 'Agent')
# profiles
profile_folder = os.path.join(agent_folder, 'profiles')
# configs
config_folder = os.path.join(agent_folder, 'configs')


def main():
    """ 主程序 LME """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init()
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        if i > 0:
            if simulator.run_round(news=(news[i-1], news[i])) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if simulator.run_round(news=(news[i-1], news[i-1])) == -1:
                print("Error occurred.")
                break
        else:
            if simulator.run_round(news=(news[0], news[i])) == -1:
                print("Error occurred.")
                break

    return 0

def main_HET(num=3):
    '''异质性消融实验'''
    assert num in [3,5,7,12],f"num={num} not in [3,5,7,12]"
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init(mode="HET",num=num)
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        if i > 0:
            if simulator.run_round(news=(news[i-1], news[i])) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if simulator.run_round(news=(news[i-1], news[i-1])) == -1:
                print("Error occurred.")
                break
        else:
            if simulator.run_round(news=(news[0], news[i])) == -1:
                print("Error occurred.")
                break

    return 0

def main_RAG():
    """ 主程序 LME RAG-Agent """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init()
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        if i > 0:
            if simulator.run_round_rag(news=(news[i-1], news[i])) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if simulator.run_round_rag(news=(news[i-1], news[i-1])) == -1:
                print("Error occurred.")
                break
        else:
            if simulator.run_round_rag(news=(news[0], news[i])) == -1:
                print("Error occurred.")
                break

    return 0


def main_ablation(mode: str='w/o expert'):
    """ 主程序 """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init()
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        if mode == 'w/o expert':
            function_name = simulator.run_round_without_expert
        elif mode == 'w/o generator':
            function_name = simulator.run_round_without_generator
        elif mode == 'w/o expert & generator':
            function_name = simulator.run_round_without_expert_and_generator
        if i > 0:
            if function_name(news=(news[i-1], news[i])) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if function_name(news=(news[i-1], news[i-1])) == -1:
                print("Error occurred.")
                break
        else:
            if function_name(news=(news[0], news[i])) == -1:
                print("Error occurred.")
                break

    return 0


def main_IH2412():
    """ 主程序 IH2412 """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init(mode='IH2412')
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        price_file = 'PricePredictionFiles/IH2412_price_generator.json'
        amount_file = 'PricePredictionFiles/IH2412_amount_generator.json'
        if i > 0:
            if simulator.run_round_new((news[i-1], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if simulator.run_round_new((news[i-1], news[i-1]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        else:
            if simulator.run_round_new((news[0], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break

    return 0


def main_TA501():
    """ 主程序 TA501 """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init(mode='TA501')
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        price_file = 'PricePredictionFiles/TA501_price_generator.json'
        amount_file = 'PricePredictionFiles/TA501_amount_generator.json'
        if i > 0:
            if simulator.run_round_new((news[i-1], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if simulator.run_round_new((news[i-1], news[i-1]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        else:
            if simulator.run_round_new((news[0], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break

    return 0

def main_SC2501():
    """ 主程序 SC2501 """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init(mode='SC2501')
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        price_file = 'PricePredictionFiles/SC2501_price_generator.json'
        amount_file = 'PricePredictionFiles/SC2501_amount_generator.json'
        if i > 0:
            if simulator.run_round_new((news[i-1], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if simulator.run_round_new((news[i-1], news[i-1]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        else:
            if simulator.run_round_new((news[0], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break

    return 0


def main_GCG2502():
    """ 主程序 SC2501 """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init(mode='GCG2502')
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        price_file = 'PricePredictionFiles/GCG2502_price_generator.json'
        amount_file = 'PricePredictionFiles/GCG2502_amount_generator.json'
        if i > 0:
            if simulator.run_round_new((news[i-1], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if simulator.run_round_new((news[i-1], news[i-1]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        else:
            if simulator.run_round_new((news[0], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break

    return 0


def main_CH2503():
    """ 主程序 CH2503 """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init(mode='CH2503')
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        price_file = 'PricePredictionFiles/CH2503_price_generator.json'
        amount_file = 'PricePredictionFiles/CH2503_amount_generator.json'
        if i > 0:
            if simulator.run_round_new((news[i-1], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        elif i == contract_round:
            if simulator.run_round_new((news[i-1], news[i-1]), price_file, amount_file) == -1:
                print("Error occurred.")
                break
        else:
            if simulator.run_round_new((news[0], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                break

    return 0


def main_SF2503():
    """ 主程序 SC2503 """
    # 计时器
    sum_time = 0.0
    last_time = time.time()
    # 初始化智能体
    agents = agents_init(mode='SF2503')
    # 初始化引擎
    engine = Engine()
    # 初始化模拟器
    simulator = Simulator(agents, engine)
    simulator.sync_system_setting()
    simulator.game_init()

    with open(os.path.join(current_path, "news.txt"), 'r', encoding='utf-8') as f:
        news = f.read().split('-----*****-----')
    with open(os.path.join(current_path, 'Agent/configs/SystemInitConfig.json'), 'r', encoding='utf-8') as f:
        contract_round = json.load(f)['contract_round']
    for i in range(contract_round+1):

        # 计时
        current_time = time.time()
        interval = current_time-last_time
        print(f"第{i}轮用时：{interval} s")
        sum_time += interval
        last_time = current_time

        torch.cuda.empty_cache()    # 清除缓存
        price_file = 'PricePredictionFiles/SF2503_price_generator.json'
        amount_file = 'PricePredictionFiles/SF2503_amount_generator.json'
        if i > 0:
            if simulator.run_round_new((news[i-1], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                return -1
        elif i == contract_round:
            if simulator.run_round_new((news[i-1], news[i-1]), price_file, amount_file) == -1:
                print("Error occurred.")
                return -1
        else:
            if simulator.run_round_new((news[0], news[i]), price_file, amount_file) == -1:
                print("Error occurred.")
                return -1

    return 0


def main_20_days_3_day_mode(futures_name, start=0, end=20):
    """
    3 交易日模拟，连续 20 天， 计 20 组
    :param futures_name: futures_name, s.t. IH2412
    :param start: index from 0-19
    :return:
    """
    with open(f'PricePredictionFiles/{futures_name}_price_20.json', 'r', encoding='utf-8') as f:
        info = json.load(f)

    for i in range(start, end):
        print(futures_name, info[i]['date'], '\nindex:', i)
        if futures_name == 'SF2503':
            news_update(
                futures_name,
                i,
                '芝加哥期货交易所大豆商品SF2503期货',
                '芝加哥期货交易所大豆商品SF2503期货价格总体保持稳定，在小范围内保持震荡，没有异动。'
            )
            init_config_update(futures_name, info[i]['date'], i)
            result = main_SF2503()
            if result != 0:
                break
        elif futures_name == 'CH2503':
            news_update(
                futures_name,
                i,
                '芝加哥期货交易所玉米商品CH2503期货',
                '芝加哥期货交易所大豆商品CH2503期货价格总体保持稳定，在小范围内保持震荡，没有异动。'
            )
            init_config_update(futures_name, info[i]['date'], i)
            result = main_CH2503()
            if result != 0:
                break
        elif futures_name == 'SC2501':
            news_update(
                futures_name,
                i,
                '上海期货交易所原油商品SC2501期货',
                '上海期货交易所原油商品SC2501期货价格总体保持稳定，在小范围内保持震荡，没有异动。'
            )
            init_config_update(futures_name, info[i]['date'], i)
            result = main_SC2501()
            if result != 0:
                break
        elif futures_name == 'TA501':
            news_update(
                futures_name,
                i,
                '郑州商品交易所精对苯二甲酸PTA商品TA501期货',
                '郑州商品交易所精对苯二甲酸PTA商品TA501期货价格总体保持稳定，在小范围内保持震荡，没有异动。'
            )
            init_config_update(futures_name, info[i]['date'], i)
            result = main_TA501()
            if result != 0:
                break
        elif futures_name == 'GCG2502':
            news_update(
                futures_name,
                i,
                '纽约商品交易所黄金GCG2502期货',
                '纽约商品交易所黄金GCG2502期货价格总体保持稳定，在小范围内保持震荡，没有异动。'
            )
            init_config_update(futures_name, info[i]['date'], i)
            result = main_GCG2502()
            if result != 0:
                break
        elif futures_name == 'IH2412':
            news_update(
                futures_name,
                i,
                '中国证券期货交易所上证50股指IH2412期货',
                '中国证券期货交易所上证50股指IH2412期货价格总体保持稳定，在小范围内保持震荡，没有异动。'
            )
            init_config_update(futures_name, info[i]['date'], i)
            result = main_IH2412()
            if result != 0:
                break

def main_parser():
    parser = argparse.ArgumentParser(
        description="批量修改 JSON 文件中的 log_file 和 dbname 字段"
    )

    parser.add_argument(
        "--folder",
        required=True,
        help="新的 log_file 文件夹路径"
    )

    parser.add_argument(
        "--db_name",
        required=True,
        help="新的数据库名"
    )

    parser.add_argument(
        "--mode",
        default="main",
        required=False,
        help="默认模式，HET为异质性实验"
    )

    parser.add_argument(
        "--num",
        default=3,
        required=False,
        help="在HET下参与实验的智能体个数"
    )

    args = parser.parse_args()
    return args

def update_json_files(folder: str, db_name: str, target_dir: str):
    """
    修改 target_dir 下所有 json 文件：
    - log_file: 只替换目录，保留文件名
    - dbname: 直接替换为 db_name
    """
    print(f"folder={folder},db_name={db_name}")
    for root, _, files in os.walk(target_dir):
        for file in files:
            if not file.endswith(".json"):
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[跳过] 无法解析 JSON：{file_path}，原因：{e}")
                continue

            modified = False

            # 处理 log_file
            if "log_file" in data and isinstance(data["log_file"], str):
                original_path = data["log_file"]
                file_name = os.path.basename(original_path)
                data["log_file"] = os.path.join("logs",folder, file_name)
                modified = True

            # 处理 dbname
            if "dbname" in data:
                data["dbname"] = db_name
                modified = True

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(
                        data,
                        f,
                        ensure_ascii=False,  #中文正常
                        indent=4
                    )
                print(f"[已更新] {file_path}")

if __name__ == '__main__':
    print('This is main')
    args=main_parser()
    update_json_files(
        folder=args.folder,
        db_name=args.db_name,
        target_dir="./Agent/configs"
    )
    main()
    # main_ablation('w/o expert')
    # main_ablation('w/o generator')
    # main_ablation('w/o expert & generator')
    # main_IH2412()
    # main_TA501()
    # main_SC2501()
    # main_GCG2502()
    # main_CH2503()
    # main_SF2503()
    # main_20_days_3_day_mode('SF2503', start=0, end=20)
    # main_RAG()