"""所有玩家智能体的类均在本文件中，包含基类与派生类"""
try:
    from .agent import AgentBasic
except:
    from agent import AgentBasic
import json, os, re

# 获取当前主程序的路径
current_path = os.path.dirname(os.path.abspath(__file__))
# templates
templates_folder = os.path.join(current_path, 'templates')

P_transaction_request = [
    ('quantity', 'amount'),
    ('close', '卖出'),
    ('open', '买入'),
    ('市价', '当前价格'),
    ('中等量', '半仓'),
    ('满', '全'),
    ('于当前', ''),
    ('最', '极'),
    ('较', '略'),
    ('稍', '略'),
    ('适量', '少量'),
    ('中量', '半仓')
]


def read_prompts(file_name):
    """
    读取 prompt 文件中的所有提示词，多轮提示词由 -----*****-----\n 分割
    保留预编译字符串的状态
    :param file_name: 文件名
    :return: 一个列表
    """
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return f.read().split("-----*****-----\n")
    except FileNotFoundError:
        print('file not found')


def response_modification(response, projects):
    """
    修改 response ，同义词替换
    :param projects: 映射列表 [(old, new)]
    """
    for p in projects:
        response = response.replace(p[0], p[1])

    return response


def extract_json(uttr: str, target_keys: list):
    """
    提取字符串中的json数据
    :param uttr: 输入字符串
    :param target_keys: 必须包含的 key 的列表
    :return: None - 失败；data - 提取出的 json 数据
    """
    pattern = re.compile(r'\{(.)*?\}')
    try:
        data = json.loads(pattern.search(uttr.replace('\n', ' ')).group(0))  # \n -> _ for re_search
    except:
        print(uttr, '\n--------uttr error--------')
        return None
    for key in target_keys:
        if key not in data.keys():
            # 检查键是否存在
            print(uttr, '\n--------key error--------')
            return None
    return data


class Player(AgentBasic):
    """ 所有玩家智能体的基类，包含统一的创建方法，数据提取方法：交易单，撮合成功，广播等 """
    def __init__(self, profile_file, config_file, security_fund_rate=12.5, limit=20):
        """
        通过文件导入人设
        :param profile_file: 人设文件路径
        """
        # load configs
        model_name = 'deepseek-v3-2-251201'
        temperature = 0.5
        top_p = 0.9
        log_file = 'log.out'
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            kws = config.keys()
            if 'model_name' in kws:
                model_name = config['model_name']
            if 'temperature' in kws:
                temperature = config['temperature']
            if 'top_p' in kws:
                top_p = config['top_p']
            if 'log_file' in kws:
                log_file = config['log_file']
            for key, value in config.items():
                setattr(self, key, value)

        # create object
        with open(profile_file, 'r', encoding='utf-8') as f:
            super().__init__(
                model_name=model_name,
                profile=f.read().strip(),
                temperature=temperature,
                top_p=top_p,
                log_file=log_file
            )

        # 统一初始化内容
        self.current_round = 0
        self.player_id = -1
        self.security_fund_rate = security_fund_rate
        self.limit = limit
        self.contract_round = 10
        self.security_deposit = 0.0
        self.available_deposit = self.original_capital
        self.capital = self.available_deposit
        self.profit = 0.0
        self.Ni_long = []
        self.Ni_short = []
        self.reflections = []   # 反思列表，用于清除上下文后回忆上一回合的行动模式

        # validity check
        assert hasattr(self, 'original_capital'), f"original_capital not in config file: {config_file}"
        assert hasattr(self, 'Nickl'), f"Nickl not in config file: {config_file}"
        assert hasattr(self, 'name'), f"name not in config file: {config_file}"

    # 修正/添加成员属性
    def round_end(self):
        """回合结束，回合数+1，返回增加后的回合数"""
        self.current_round += 1
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f'-------------第{self.current_round-1}回合结束-------------\n\n_new round_\n')
        return self.current_round

    def set_id(self, new_id: int):
        """
        为模拟角色设置交易中的新id（唯一），以便于数据库管理
        :param new_id: new ID
        """
        self.player_id = new_id

    def sync_system_setting(self, security_fund_rate, limit, contract_round):
        """同步系统设定，security_fund_rate & limit & contract_round"""
        self.security_fund_rate = security_fund_rate
        self.limit = limit
        self.contract_round = contract_round

    def refresh_account_info(self, account_info):
        """ 查询数据库，刷新个人信息 """
        self.capital = float(account_info['capital'])
        self.security_deposit = float(account_info['security_deposit'])
        self.available_deposit = float(account_info['available_deposit'])
        self.Ni_long = account_info['Ni_long']
        self.Ni_short = account_info['Ni_short']
        self.profit = account_info['profit_loss']
        return 0

    # 查询成员属性
    def get_id(self):
        """查询在游戏中的ID"""
        return self.player_id

    def get_name(self):
        """返回玩家名称"""
        return self.name

    def get_capital(self):
        """获取当前资产"""
        return self.capital

    def get_profile(self):
        """获取用户资料"""
        return self.profile

    def get_fund_supplement(self):
        """获得每回合初，补充资金的量"""
        return self.fund_supplement

    # 账户信息格式化
    def account_info_formatter(self):
        """format self.Ni_short/long: list -> str"""
        # Ni_long
        msg_long = "没有买单交易"
        total_volume = 0
        weighted_sum = 0

        for volume, price in self.Ni_long:
            total_volume += float(volume)
            weighted_sum += float(volume) * float(price)

        if total_volume == 0:
            pass
        else:
            weighted_average_price = weighted_sum / total_volume
            msg_long = f"买单（看多）订单总量：{total_volume:.2f} 手, 平均成交价格：{weighted_average_price:.4f} 元/手".format(
                total_volume=total_volume,
                weighted_average_price=weighted_average_price
            )

        # Ni_short
        msg_short = "没有卖单交易"
        total_volume = 0
        weighted_sum = 0

        for volume, price in self.Ni_short:
            total_volume += float(volume)
            weighted_sum += float(volume) * float(price)

        if total_volume == 0:
            pass
        else:
            weighted_average_price = weighted_sum / total_volume
            msg_short = f"卖单（看空）订单总量：{total_volume:.2f} 手, 平均成交价格：{weighted_average_price:.4f} 元/手".format(
                total_volume=total_volume,
                weighted_average_price=weighted_average_price
            )
        return msg_long, msg_short


class QingShanPlayer(Player):
    """
    通过 Player 类派生的青山类
    """

    def game_start(self):
        """
        打开 ./templates/QingShan/QingShan_game_start.txt 向 QingShanPlayer 确定游戏规则和目标等信息
        :return: 0 - 不删除任何对话
        """
        turns = 1   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/QingShan_game_start.txt'))
        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    fund_supplement=self.fund_supplement,
                    original_capital=self.original_capital,
                    Nickl=self.Nickl,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    contract_round=self.contract_round
                )
                self.chat_with_log(prompt)
        return 0

    def news_analysis(self, news: str, expert_observation: str):
        """
        第 self.current_round 轮的新闻分析
        :param news: 新闻内容
        :param expert_observation: 专家对新闻的分析，用于补充一部分专业知识
        :return: 4 - 4 轮对话待删除
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_news_analysis.txt'))

        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    round=self.current_round,
                    news=news
                )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i].format(
                    expert_observation=expert_observation
                )
                self.chat_with_log(prompt)
        return 2 * turns

    def news_analysis_rag(self, news: str, rag_info: str):
        """
        第 self.current_round 轮的新闻分析
        :param news: 新闻内容
        :param expert_observation: 专家对新闻的分析，用于补充一部分专业知识
        :return: 4 - 4 轮对话待删除
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_news_analysis_rag.txt'))

        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    round=self.current_round,
                    news=news
                )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i].format(
                    rag_info=rag_info
                )
                self.chat_with_log(prompt)
        return 2 * turns

    def market_info_analysis(self, retrieved_info: dict):
        """
        由引擎检索市场信息，并由智能体进行分析
        :param retrieved_info: 字典 - 包括 current_Ni_price, Ni_inventory, Ni_holder, last_turn_trades
        :return: 6, data - 6 轮对话需要删除, 回合开始阶段看涨还是看跌
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_market_info_analysis.txt'))
        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    current_Ni_price=retrieved_info['current_Ni_price'],
                    Ni_inventory=retrieved_info['Ni_inventory'],
                    Ni_holder=str(retrieved_info['Ni_holder']),
                    last_turn_trades=str(retrieved_info['last_turn_trades'])
                )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                # 提取json数据
                pattern = re.compile(r'\{(.)*\}')
                try:
                    data = json.loads(pattern.search(response['content'].replace('\n', ' ')).group(0))  # \n -> _ for re_search
                    if 'judgement' not in data.keys():
                        print(response, '\n--------key error--------')
                        self.remove_agent_context(-2)
                        return None
                    elif not isinstance(data['judgement'], str):
                        print(response, '\n--------value error--------')
                        self.remove_agent_context(-2)
                        return None
                    return 2 * turns, data
                except Exception as e:
                    print(e)
                    print(response, '\n--------format error--------')
                    self.remove_agent_context(-2)
                    return None, None

    def account_info_confirmation(self):
        """
        确认当前回合账户状态
        :param self.account_info 必须包含以下字段
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :return: 2 - 2 轮对话需删除
        """
        turns = 1   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_account_info_confirmation.txt'))

        for i in range(turns):
            if i == 0:
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)

        return 2 * turns

    def transaction_request_phase_1(self, current_turn, attitude):
        """
        每一轮交易的第一阶段，确认是否参与这一轮交易，以及交易策略，待专家评估
        :param current_turn: 当前交易轮次
        :param self.account_info: 包含以下信息
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :param attitude: 当前回合对于期货价格的态度
        :return: (4, Dict["anticipation"]="否", None) or (6, Dict["anticipation"]="是", 策略); (None, None, None) 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_transaction_request.txt'))
        returnList = []

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    round=self.current_round,
                    num_order=current_turn,
                    attitude=attitude,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["anticipation"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] not in ["是", "否"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] == "否":
                        return 2*(i+1), data, None
                    else:
                        returnList.append(data)
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None, None
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                return 2 * turns, returnList[0], response['content']

    def transaction_request_phase_2(self, expert_advise):
        """
        每一轮交易的第二阶段，确认参与这一轮交易后，给出出价模式
        :param expert_advise: 专家对策略的评价
        :return: 4, dataDict; None, None
        dataDict - {
            "type": <买入 or 卖出>,
            "amount": <少量 or 半仓 or 大量 or 全仓>,
            "price": <买入/卖出期货的价格>
        } ;
        None - 失败
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_transaction_request.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                prompt = prompts[i+3].format(
                    expert_advise=expert_advise
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i+3]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(
                        response_modification(response['content'], P_transaction_request),
                        ["type", "amount", "price"]
                    )
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["type"] not in ["买入", "卖出"]:
                        # value error
                        print('--------- value error --------- in "type"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["amount"] not in ["少量", "半仓", "大量", "全仓"]:
                        # value error
                        print('--------- value error --------- in "amount"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["price"] not in ["当前价格", "更高价格", "更低价格", "略高价格", "略低价格", "极高价格", "极低价格"]:
                        # value error
                        print('--------- value error --------- in "price"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    print(response['content'])
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None

    def transaction_response_and_withdraw(self, message, request_info):
        """
        每一轮交易的第三阶段，确认本轮出价后的交易达成情况，决定是否撤单
        这一模式下，没有专家参与
        :param message: 交易达成情况确认
        :param request_info: 全局请求量信息
        :return: 6, data ; None, None
        data - {"amount": str}
        None - 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'transaction_response.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                prompt = prompts[i].format(
                    message=message,
                    buy_amount=request_info[0],
                    buy_price=request_info[1],
                    sell_amount=request_info[2],
                    sell_price=request_info[3]
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 决定是否撤单
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                # 确认撤单策略
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["withdrawal"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["withdrawal"] not in ["不撤单", "少量", "一半", "大量", "全部"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                return None, None

    def current_round_strategy_reflection(self):
        """
        对当前回合状态的反思，并保存至策略列表 self.reflections，用于下一回合最初的提示词
        :return: 2 - 2 轮对话需要删除
        """
        turns = 1
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_current_round_strategy_reflection.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.reflections.append(self.chat_with_log(prompt)['content'])

        return 2 * turns

    def review_reflection(self):
        """
        在回合开始的最初阶段回顾上一轮的 reflection
        :return: 2 - 2 轮对话待删除
        """
        turns = 1
        self.chat.append_context("请你回顾你上一轮的策略和反思。")
        self.chat.append_context(
            "我上一轮的策略和反思是：\n{reflection:s}\n".format(reflection=self.reflections[-1]),
            role="assistant"
        )
        return 2 * turns

    # ablation study
    def transaction_request_phase_1_without_generator(self, current_turn, attitude):
        """
        每一轮交易的第一阶段，确认是否参与这一轮交易，以及交易策略，待专家评估
        :param current_turn: 当前交易轮次
        :param self.account_info: 包含以下信息
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :param attitude: 当前回合对于期货价格的态度
        :return: (4, Dict["anticipation"]="否", None) or (6, Dict["anticipation"]="是", 策略); (None, None, None) 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_transaction_request_without_generator.txt'))
        returnList = []

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    round=self.current_round,
                    num_order=current_turn,
                    attitude=attitude,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["anticipation"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] not in ["是", "否"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] == "否":
                        return 2*(i+1), data, None
                    else:
                        returnList.append(data)
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None, None
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                return 2 * turns, returnList[0], response['content']

    def transaction_request_phase_2_without_generator(self, expert_advise):
        """
        每一轮交易的第二阶段，确认参与这一轮交易后，给出出价模式
        :param expert_advise: 专家对策略的评价
        :return: 4, dataDict; None, None
        dataDict - {
            "type": <买入 or 卖出>,
            "amount": <少量 or 半仓 or 大量 or 全仓>,
            "price": <买入/卖出期货的价格>
        } ;
        None - 失败
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_transaction_request_without_generator.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                prompt = prompts[i+3].format(
                    expert_advise=expert_advise
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i+3]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(
                        response_modification(response['content'], P_transaction_request),
                        ["type", "amount", "price"]
                    )
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["type"] not in ["买入", "卖出"]:
                        # value error
                        print('--------- value error --------- in "type"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["amount"] > 100.0 or data["amount"] < 0.0:
                        # value error
                        print('--------- value error --------- in "amount"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["price"] > 100.0 or data["price"] < -100.0:
                        # value error
                        print('--------- value error --------- in "price"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    print(response['content'])
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None
    def transaction_response_and_withdraw_without_generator(self, message, request_info):
        """
    每一轮交易的第三阶段，确认本轮出价后的交易达成情况，决定是否撤单
    这一模式下，没有专家参与
    :param message: 交易达成情况确认
    :param request_info: 全局请求量信息
    :return: 6, data ; None, None
    data - {"amount": str}
    None - 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'transaction_response_without_generator.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                prompt = prompts[i].format(
                    message=message,
                    buy_amount=request_info[0],
                    buy_price=request_info[1],
                    sell_amount=request_info[2],
                    sell_price=request_info[3]
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 决定是否撤单
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                # 确认撤单策略
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["withdrawal"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["withdrawal"] > 100.0 or data["withdrawal"] < 0.0:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                return None, None


class GlencorePlayer(Player):
    """
    通过 Player 类派生的 Glencore 类
    """

    def game_start(self):
        """
        打开 ./templates/Glencore/Glencore_game_start.txt 向 QingShanPlayer 确定游戏规则和目标等信息
        :return: 0
        """
        prompts = read_prompts(os.path.join(templates_folder, 'Glencore/Glencore_game_start.txt'))
        for i in range(1):
            if i == 0:
                prompt = prompts[0].format(
                    fund_supplement=self.fund_supplement,
                    original_capital=self.original_capital,
                    Nickl=self.Nickl,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    contract_round=self.contract_round
                )
                self.chat_with_log(prompt)
        return 0

    def news_analysis(self, news: str, expert_observation: str):
        """
        第 self.current_round 轮的新闻分析
        :param news: 新闻内容
        :param expert_observation: 专家对新闻的分析，用于补充一部分专业知识
        :return: 4 - 4 轮对话待删除
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'Glencore/Glencore_news_analysis.txt'))

        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    round=self.current_round,
                    news=news
                )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i].format(
                    expert_observation=expert_observation
                )
                self.chat_with_log(prompt)
        return 2 * turns

    def news_analysis_rag(self, news: str, rag_info: str):
        """
        第 self.current_round 轮的新闻分析
        :param news: 新闻内容
        :param expert_observation: 专家对新闻的分析，用于补充一部分专业知识
        :return: 4 - 4 轮对话待删除
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'Glencore/Glencore_news_analysis_rag.txt'))

        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    round=self.current_round,
                    news=news
                )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i].format(
                    rag_info=rag_info
                )
                self.chat_with_log(prompt)
        return 2 * turns

    def market_info_analysis(self, retrieved_info: dict):
        """
        由引擎检索市场信息，并由智能体进行分析
        :param retrieved_info: 字典 - 包括 current_Ni_price, Ni_inventory, Ni_holder, last_turn_trades
        :return: 6, data - 6 轮对话需要删除, 回合开始阶段看涨还是看跌
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'Glencore/Glencore_market_info_analysis.txt'))
        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    current_Ni_price=retrieved_info['current_Ni_price'],
                    Ni_inventory=retrieved_info['Ni_inventory'],
                    Ni_holder=str(retrieved_info['Ni_holder']),
                    last_turn_trades=str(retrieved_info['last_turn_trades'])
                )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                # 提取json数据
                pattern = re.compile(r'\{(.)*\}')
                try:
                    data = json.loads(pattern.search(response['content'].replace('\n', ' ')).group(0))  # \n -> _ for re_search
                    if 'judgement' not in data.keys():
                        print(response, '\n--------key error--------')
                        self.remove_agent_context(-2)
                        return None
                    elif not isinstance(data['judgement'], str):
                        print(response, '\n--------value error--------')
                        self.remove_agent_context(-2)
                        return None
                    return 2 * turns, data
                except Exception as e:
                    print(e)
                    print(response, '\n--------format error--------')
                    self.remove_agent_context(-2)
                    return None, None

    def account_info_confirmation(self):
        """
        确认当前回合账户状态
        :param self.account_info 必须包含以下字段
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :return: 2 - 2 轮对话需删除
        """
        turns = 1   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'Glencore/Glencore_account_info_confirmation.txt'))

        for i in range(turns):
            if i == 0:
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)

        return 2 * turns

    def transaction_request_phase_1(self, current_turn, attitude):
        """
        每一轮交易的第一阶段，确认是否参与这一轮交易，以及交易策略，待专家评估
        :param current_turn: 当前交易轮次
        :param self.account_info: 包含以下信息
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :param attitude: 当前回合对于期货价格的态度
        :return: (4, Dict["anticipation"]="否", None) or (6, Dict["anticipation"]="是", 策略); (-1, None, None) 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'Glencore/Glencore_transaction_request.txt'))
        returnList = []

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    round=self.current_round,
                    num_order=current_turn,
                    attitude=attitude,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["anticipation"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] not in ["是", "否"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] == "否":
                        return 2*(i+1), data, None
                    else:
                        returnList.append(data)
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None, None
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                return 2 * turns, returnList[0], response['content']

    def transaction_request_phase_2(self, expert_advise):
        """
        每一轮交易的第二阶段，确认参与这一轮交易后，给出出价模式
        :param expert_advise: 专家对策略的评价
        :return: 4, dataDict; None, None
        dataDict - {
            "type": <买入 or 卖出>,
            "amount": <少量 or 半仓 or 大量 or 全仓>,
            "price": <买入/卖出期货的价格>
        } ;
        None - 失败
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'Glencore/Glencore_transaction_request.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                prompt = prompts[i+3].format(
                    expert_advise=expert_advise
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i+3]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(
                        response_modification(response['content'], P_transaction_request),
                        ["type", "amount", "price"]
                    )
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["type"] not in ["买入", "卖出"]:
                        # value error
                        print('--------- value error --------- in "type"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["amount"] not in ["少量", "半仓", "大量", "全仓"]:
                        # value error
                        print('--------- value error --------- in "amount"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["price"] not in ["当前价格", "更高价格", "更低价格", "略高价格", "略低价格", "极高价格", "极低价格"]:
                        # value error
                        print('--------- value error --------- in "price"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    print(response['content'])
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None

    def transaction_response_and_withdraw(self, message, request_info):
        """
        每一轮交易的第三阶段，确认本轮出价后的交易达成情况，决定是否撤单
        这一模式下，没有专家参与
        :param message: 交易达成情况确认
        :param request_info: 全局请求量信息
        :return: 6, data ; None, None
        data - {"amount": str}
        None - 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'transaction_response.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                prompt = prompts[i].format(
                    message=message,
                    buy_amount=request_info[0],
                    buy_price=request_info[1],
                    sell_amount=request_info[2],
                    sell_price=request_info[3]
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 决定是否撤单
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                # 确认撤单策略
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["withdrawal"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["withdrawal"] not in ["不撤单", "少量", "一半", "大量", "全部"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                return None, None

    def current_round_strategy_reflection(self):
        """
        对当前回合状态的反思，并保存至策略列表 self.reflections，用于下一回合最初的提示词
        :return: 2 - 2 轮对话需要删除
        """
        turns = 1
        prompts = read_prompts(os.path.join(templates_folder, 'Glencore/Glencore_current_round_strategy_reflection.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.reflections.append(self.chat_with_log(prompt)['content'])

        return 2 * turns

    def review_reflection(self):
        """
        在回合开始的最初阶段回顾上一轮的 reflection
        :return: 2 - 2 轮对话待删除
        """
        turns = 1
        self.chat.append_context("请你回顾你上一轮的策略和反思。")
        self.chat.append_context(
            "我上一轮的策略和反思是：\n{reflection:s}\n".format(reflection=self.reflections[-1]),
            role="assistant"
        )
        return 2 * turns

    # ablation study
    def transaction_request_phase_1_without_generator(self, current_turn, attitude):
        """
        每一轮交易的第一阶段，确认是否参与这一轮交易，以及交易策略，待专家评估
        :param current_turn: 当前交易轮次
        :param self.account_info: 包含以下信息
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :param attitude: 当前回合对于期货价格的态度
        :return: (4, Dict["anticipation"]="否", None) or (6, Dict["anticipation"]="是", 策略); (None, None, None) 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_transaction_request_without_generator.txt'))
        returnList = []

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    round=self.current_round,
                    num_order=current_turn,
                    attitude=attitude,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["anticipation"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] not in ["是", "否"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] == "否":
                        return 2*(i+1), data, None
                    else:
                        returnList.append(data)
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None, None
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                return 2 * turns, returnList[0], response['content']

    def transaction_request_phase_2_without_generator(self, expert_advise):
        """
        每一轮交易的第二阶段，确认参与这一轮交易后，给出出价模式
        :param expert_advise: 专家对策略的评价
        :return: 4, dataDict; None, None
        dataDict - {
            "type": <买入 or 卖出>,
            "amount": <少量 or 半仓 or 大量 or 全仓>,
            "price": <买入/卖出期货的价格>
        } ;
        None - 失败
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_transaction_request_without_generator.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                prompt = prompts[i+3].format(
                    expert_advise=expert_advise
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i+3]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(
                        response_modification(response['content'], P_transaction_request),
                        ["type", "amount", "price"]
                    )
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["type"] not in ["买入", "卖出"]:
                        # value error
                        print('--------- value error --------- in "type"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["amount"] > 100.0 or data["amount"] < 0.0:
                        # value error
                        print('--------- value error --------- in "amount"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["price"] > 100.0 or data["price"] < -100.0:
                        # value error
                        print('--------- value error --------- in "price"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    print(response['content'])
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None

    def transaction_response_and_withdraw_without_generator(self, message, request_info):
        """
    每一轮交易的第三阶段，确认本轮出价后的交易达成情况，决定是否撤单
    这一模式下，没有专家参与
    :param message: 交易达成情况确认
    :param request_info: 全局请求量信息
    :return: 6, data ; None, None
    data - {"amount": str}
    None - 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'transaction_response_without_generator.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                prompt = prompts[i].format(
                    message=message,
                    buy_amount=request_info[0],
                    buy_price=request_info[1],
                    sell_amount=request_info[2],
                    sell_price=request_info[3]
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 决定是否撤单
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                # 确认撤单策略
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["withdrawal"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["withdrawal"] > 100.0 or data["withdrawal"] < 0.0:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                return None, None


class OrdinaryPlayers(Player):
    """
    散户玩家，由 Player 派生
    """
    def game_start(self):
        """
        普通玩家游戏开始
        打开 "./templates/game_start.txt"
        :return: 0
        """
        prompts = read_prompts(os.path.join(templates_folder, 'game_start.txt'))
        for i in range(1):
            if i == 0:
                prompt = prompts[0].format(
                    fund_supplement=self.fund_supplement,
                    original_capital=self.original_capital,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    contract_round=self.contract_round
                )
                self.chat_with_log(prompt)
        return 0

    def news_analysis(self, news: str, expert_observation: str):
        """
        第 self.current_round 轮的新闻分析
        :param news: 新闻内容
        :param expert_observation: 专家对新闻的分析，用于补充一部分专业知识
        :return: 4 - 4 轮对话待删除
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'news_analysis.txt'))

        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    round=self.current_round,
                    news=news
                )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i].format(
                    expert_observation=expert_observation
                )
                self.chat_with_log(prompt)
        return 2 * turns

    def news_analysis_rag(self, news: str, rag_info: str):
        """
        第 self.current_round 轮的新闻分析
        :param news: 新闻内容
        :param expert_observation: 专家对新闻的分析，用于补充一部分专业知识
        :return: 4 - 4 轮对话待删除
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'news_analysis_rag.txt'))

        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    round=self.current_round,
                    news=news
                )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i].format(
                    rag_info=rag_info
                )
                self.chat_with_log(prompt)
        return 2 * turns

    def market_info_analysis(self, retrieved_info: dict):
        """
        由引擎检索市场信息，并由智能体进行分析
        :param retrieved_info: 字典 - 包括 current_Ni_price, Ni_inventory, Ni_holder, last_turn_trades
        :return: 6, data - 6 轮对话需要删除, 回合开始阶段看涨还是看跌
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'market_info_analysis.txt'))
        for i in range(turns):
            if i == 0:
                if len(retrieved_info['last_turn_trades']['long(buy)']) > 0:
                    prompt = prompts[i].format(
                        current_Ni_price=retrieved_info['current_Ni_price'],
                        Ni_inventory=retrieved_info['Ni_inventory'],
                        Ni_holder=str(retrieved_info['Ni_holder']),
                        last_turn_trades=str(retrieved_info['last_turn_trades'])
                    )
                else:
                    prompt = prompts[i].format(
                        current_Ni_price=retrieved_info['current_Ni_price'],
                        Ni_inventory=retrieved_info['Ni_inventory'],
                        Ni_holder='未公开',
                        last_turn_trades='未公开'
                    )
                self.chat_with_log(prompt)
            elif i == 1:
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                # 提取json数据
                pattern = re.compile(r'\{(.)*\}')
                try:
                    data = json.loads(pattern.search(response['content'].replace('\n', ' ')).group(0))  # \n -> _ for re_search
                    if 'judgement' not in data.keys():
                        print(response, '\n--------key error--------')
                        self.remove_agent_context(-2)
                        return None
                    elif not isinstance(data['judgement'], str):
                        print(response, '\n--------value error--------')
                        self.remove_agent_context(-2)
                        return None
                    return 2 * turns, data
                except Exception as e:
                    print(e)
                    print(response, '\n--------format error--------')
                    self.remove_agent_context(-2)
                    return None, None

    def account_info_confirmation(self):
        """
        确认当前回合账户状态
        :param self.account_info 必须包含以下字段
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :return: 2 - 2 轮对话需删除
        """
        turns = 1   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'account_info_confirmation.txt'))

        for i in range(turns):
            if i == 0:
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)

        return 2 * turns

    def transaction_request_phase_1(self, current_turn, attitude):
        """
        每一轮交易的第一阶段，确认是否参与这一轮交易，以及交易策略，待专家评估
        :param current_turn: 当前交易轮次
        :param self.account_info: 包含以下信息
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :param attitude: 当前回合对于期货价格的态度
        :return: (4, Dict["anticipation"]="否", None) or (6, Dict["anticipation"]="是", 策略); (-1, None, None) 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'transaction_request.txt'))
        returnList = []

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    round=self.current_round,
                    num_order=current_turn,
                    attitude=attitude,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["anticipation"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] not in ["是", "否"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] == "否":
                        return 2*(i+1), data, None
                    else:
                        returnList.append(data)
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None, None
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                return 2 * turns, returnList[0], response['content']

    def transaction_request_phase_2(self, expert_advise):
        """
        每一轮交易的第二阶段，确认参与这一轮交易后，给出出价模式
        :param expert_advise: 专家对策略的评价
        :return: 4, dataDict; None, None
        dataDict - {
            "type": <买入 or 卖出>,
            "amount": <少量 or 半仓 or 大量 or 全仓>,
            "price": <买入/卖出期货的价格>
        } ;
        None - 失败
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'transaction_request.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                prompt = prompts[i+3].format(
                    expert_advise=expert_advise
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i+3]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(
                        response_modification(response['content'], P_transaction_request),
                        ["type", "amount", "price"]
                    )
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["type"] not in ["买入", "卖出"]:
                        # value error
                        print('--------- value error --------- in "type"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["amount"] not in ["少量", "半仓", "大量", "全仓"]:
                        # value error
                        print('--------- value error --------- in "amount"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["price"] not in ["当前价格", "更高价格", "更低价格", "略高价格", "略低价格", "极高价格", "极低价格"]:
                        # value error
                        print('--------- value error --------- in "price"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    print(response['content'])
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None

    def transaction_response_and_withdraw(self, message, request_info):
        """
        每一轮交易的第三阶段，确认本轮出价后的交易达成情况，决定是否撤单
        这一模式下，没有专家参与
        :param message: 交易达成情况确认
        :param request_info: 全局请求量信息
        :return: 6, data ; None, None
        data - {"amount": str}
        None - 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'transaction_response.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                prompt = prompts[i].format(
                    message=message,
                    buy_amount=request_info[0],
                    buy_price=request_info[1],
                    sell_amount=request_info[2],
                    sell_price=request_info[3]
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 决定是否撤单
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                # 确认撤单策略
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["withdrawal"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["withdrawal"] not in ["不撤单", "少量", "一半", "大量", "全部"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                return None, None

    def current_round_strategy_reflection(self):
        """
        对当前回合状态的反思，并保存至策略列表 self.reflections，用于下一回合最初的提示词
        :return: 2 - 2 轮对话需要删除
        """
        turns = 1
        prompts = read_prompts(os.path.join(templates_folder, 'current_round_strategy_reflection.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    profit_loss=self.profit
                )
                self.reflections.append(self.chat_with_log(prompt)['content'])

        return 2 * turns

    def review_reflection(self):
        """
        在回合开始的最初阶段回顾上一轮的 reflection
        :return: 2 - 2 轮对话待删除
        """
        turns = 1
        self.chat.append_context("请你回顾你上一轮的策略和反思。")
        self.chat.append_context(
            "我上一轮的策略和反思是：\n{reflection:s}\n".format(reflection=self.reflections[-1]),
            role="assistant"
        )
        return 2 * turns

    # ablation study
    def transaction_request_phase_1_without_generator(self, current_turn, attitude):
        """
        每一轮交易的第一阶段，确认是否参与这一轮交易，以及交易策略，待专家评估
        :param current_turn: 当前交易轮次
        :param self.account_info: 包含以下信息
        capital - 总资产 float
        security_deposit - 保证金 float
        available_deposit - 可用资金 float
        Ni_long - 多头合约（持有的买单信息） list
        Ni_short -  空头合约（持有的卖单信息） list
        :param attitude: 当前回合对于期货价格的态度
        :return: (4, Dict["anticipation"]="否", None) or (6, Dict["anticipation"]="是", 策略); (None, None, None) 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_transaction_request_without_generator.txt'))
        returnList = []

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                Ni_long, Ni_short = self.account_info_formatter()
                prompt = prompts[i].format(
                    round=self.current_round,
                    num_order=current_turn,
                    attitude=attitude,
                    security_fund_rate=self.security_fund_rate,
                    limit=self.limit,
                    capital=self.capital,
                    security_deposit=self.security_deposit,
                    available_deposit=self.available_deposit,
                    Ni_long=Ni_long,
                    Ni_short=Ni_short,
                    Nickl=self.Nickl,
                    profit_loss=self.profit
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["anticipation"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] not in ["是", "否"]:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None, None
                    if data["anticipation"] == "否":
                        return 2*(i+1), data, None
                    else:
                        returnList.append(data)
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None, None
            elif i == 2:
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                return 2 * turns, returnList[0], response['content']

    def transaction_request_phase_2_without_generator(self, expert_advise):
        """
        每一轮交易的第二阶段，确认参与这一轮交易后，给出出价模式
        :param expert_advise: 专家对策略的评价
        :return: 4, dataDict; None, None
        dataDict - {
            "type": <买入 or 卖出>,
            "amount": <少量 or 半仓 or 大量 or 全仓>,
            "price": <买入/卖出期货的价格>
        } ;
        None - 失败
        """
        turns = 2   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'QingShan/Qingshan_transaction_request_without_generator.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次信息
                prompt = prompts[i+3].format(
                    expert_advise=expert_advise
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 确认是否下单
                prompt = prompts[i+3]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(
                        response_modification(response['content'], P_transaction_request),
                        ["type", "amount", "price"]
                    )
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["type"] not in ["买入", "卖出"]:
                        # value error
                        print('--------- value error --------- in "type"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["amount"] > 100.0 or data["amount"] < 0.0:
                        # value error
                        print('--------- value error --------- in "amount"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["price"] > 100.0 or data["price"] < -100.0:
                        # value error
                        print('--------- value error --------- in "price"')
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    print(response['content'])
                    self.remove_agent_context(-2 * (i + 1))
                    return None, None

    def transaction_response_and_withdraw_without_generator(self, message, request_info):
        """
    每一轮交易的第三阶段，确认本轮出价后的交易达成情况，决定是否撤单
    这一模式下，没有专家参与
    :param message: 交易达成情况确认
    :param request_info: 全局请求量信息
    :return: 6, data ; None, None
    data - {"amount": str}
    None - 失败
        """
        turns = 3   # 对话轮数
        prompts = read_prompts(os.path.join(templates_folder, 'transaction_response_without_generator.txt'))

        for i in range(turns):
            if i == 0:
                # 确认当前轮次撮合结果信息
                prompt = prompts[i].format(
                    message=message,
                    buy_amount=request_info[0],
                    buy_price=request_info[1],
                    sell_amount=request_info[2],
                    sell_price=request_info[3]
                )
                self.chat_with_log(prompt)
            elif i == 1:
                # 决定是否撤单
                prompt = prompts[i]
                self.chat_with_log(prompt)
            elif i == 2:
                # 确认撤单策略
                prompt = prompts[i]
                response = self.chat_with_log(prompt)

                try:
                    data = extract_json(response['content'], ["withdrawal"])
                    if data is None:
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None
                    if data["withdrawal"] > 100.0 or data["withdrawal"] < 0.0:
                        # value error
                        self.remove_agent_context(-2 * (i + 1))
                        return None, None

                    return 2 * turns, data
                except all:
                    self.remove_agent_context(-2 * (i + 1))
                return None, None


def main():
    """ main """
    print("this is main()")
    GLE_test = GlencorePlayer(
        profile_file='./profiles/GlencoreProfile0.txt',
        config_file='./configs/GlencoreConfig.json'
    )
    GLE_test.game_start()
    print("main() ends")


if __name__ == '__main__':
    main()