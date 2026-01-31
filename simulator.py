"""模拟器类，通过调用引擎和智能体，完成模拟过程"""
import json
from utils import *
from faiss_vector import retrieve_query
from Agent.CFGPT import CFGPT

class Simulator:
    """
    模拟器类，包含期货模拟过程中的所有环节
    """
    def __init__(self, agents: list, engine, config_file=None):
        """
        初始化函数。一系列智能体和引擎构成模拟器
        :param agents: 智能体列表，其中的智能体必须是 Agent.players.Player 的子类
        :param engine: 引擎是引擎类
        """
        self.agents = agents
        self.engine = engine
        self.expert = CFGPT()
        self.current_round = 0

        # 其它系统配置信息
        if config_file is None:
            config_file = "./Agent/configs/SystemInitConfig.json"
        with open(config_file, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        for key, value in configs.items():
            setattr(self, key, value)

    def sync_system_setting(self):
        """同步系统设置，security_fund_rate & limit"""
        for agent in self.agents:
            agent.sync_system_setting(self.security_fund_rate, self.limit, self.contract_round)

        self.engine.sync_system_setting(self.security_fund_rate, self.limit, self.contract_round)

    def game_init(self):
        """
        游戏开始阶段，所有玩家依次确认他们的身份和游戏规则
        :return: 0 - success
        """
        for agent in self.agents:
            agent.game_start()
        self.engine.engine_init(
            self.dbname,
            self.agents,
            self.initial_futures_price,
            self.initial_actuals_price,
            self.Ni_inventory
        )

        return 0

    def run_round(self, news: tuple[str, str]):
        """
        游戏的第 self.current_round 回合，出现新闻 news
        :param news: （上一回合新闻，本回合新闻）
        :return: 0
        """

        # 同步回合信息
        self.current_round += 1
        assert self.engine.round_end() == self.current_round, "Engine round number is out of sync"
        for agent in self.agents:
            assert agent.round_end() == self.current_round, "agent round number is out of sync"

        if self.current_round == self.contract_round + 1:
            return 0

        # 追加资金
        for agent in self.agents:
            self.engine.fund_supplement(agent.get_id(), agent.get_fund_supplement())

        # retrieve info
        retrieved_market_info = self.engine.retrieve_market_info()
        # analyze news, market info
        first_judgements = {}   # 本轮的最初态度

        # 对话删除计数
        uttrs_to_be_removed = {}
        if self.current_round == 1:
            # 第一回合，没有上一轮策略的对话，从零开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = 0
        else:
            # 包含上一轮的策略，从确认上一轮策略使用的对话轮数开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = agent.review_reflection()

        # 回合开始
        for agent in self.agents:
            # 打印状态
            print(f'\n----****----\nround {self.current_round}, agent {agent.get_name()} starts\n----****----')
            # print(f'current context:\n{agent.get_context()}\n----****----')
            # 智能体对新闻的分析
            pass_list = [
                '大宗商品贸易集团',
                '全球性综合金属生产集团',
                'InstitutionalProfile0',
                'InstitutionalProfile1',
                'InstitutionalProfile2',
                'InstitutionalProfile3',
            ]
            if agent.get_name() not in pass_list:
                # 玩家是普通玩家才会有延迟判定
                got_news = news_delay(news)     # 新闻延迟
            else:
                got_news = news[-1]
            # 专家模型对新闻的分析
            expert_observation = self.expert.news_analysis(got_news)
            uttrs_to_be_removed[str(agent.get_id())] += agent.news_analysis(got_news, expert_observation)
            # 分析市场信息，生成交易前看多与看空倾向
            for _ in range(5):
                count, judgement_0 = agent.market_info_analysis(retrieved_market_info)
                if count is not None:
                    break
            else:
                print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - market info analysis.")
                return -1

            # 对话成功后
            uttrs_to_be_removed[str(agent.get_id())] += count
            first_judgements[str(agent.get_id())] = judgement_0['judgement']

            # 同步与确认账户信息
            account_info = self.engine.retrieve_account_info(agent.get_id())
            agent.refresh_account_info(account_info)
            uttrs_to_be_removed[str(agent.get_id())] += agent.account_info_confirmation()

        # 出价与交易撮合
        temp_dict_1, succeeded_requests, failed_requests, deals = self.trade_phase(
            first_judgements,
            retrieved_market_info
        )

        # 出价与交易撮合过程中出错
        if temp_dict_1 is None:
            return -1

        # 回合结束，账户结算，与本轮策略保存，用于下一回合
        temp_dict_2 = self.settlement_phase()

        # 计数，并删除提示词
        for agent in self.agents:
            key = str(agent.get_id())
            uttrs_to_be_removed[key] += temp_dict_1[key]
            uttrs_to_be_removed[key] += temp_dict_2[key]
            agent.remove_agent_context(
                beginning=-1*uttrs_to_be_removed[key],
            )
            prompt, completion = agent.get_usage()
            print(
                f"\n----------tokens----------\n"
                f"已使用 tokens: prompt - {prompt}; completion - {completion} \n"
                f"--------------------------\n"
            )

        return 0

    def run_round_rag(self, news: tuple[str, str]):
        """
        游戏的第 self.current_round 回合，出现新闻 news
        :param news: （上一回合新闻，本回合新闻）
        :return: 0
        """

        # 同步回合信息
        self.current_round += 1
        assert self.engine.round_end() == self.current_round, "Engine round number is out of sync"
        for agent in self.agents:
            assert agent.round_end() == self.current_round, "agent round number is out of sync"

        if self.current_round == self.contract_round + 1:
            return 0

        # 追加资金
        for agent in self.agents:
            self.engine.fund_supplement(agent.get_id(), agent.get_fund_supplement())

        # retrieve info
        retrieved_market_info = self.engine.retrieve_market_info()
        # analyze news, market info
        first_judgements = {}   # 本轮的最初态度

        # 对话删除计数
        uttrs_to_be_removed = {}
        if self.current_round == 1:
            # 第一回合，没有上一轮策略的对话，从零开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = 0
        else:
            # 包含上一轮的策略，从确认上一轮策略使用的对话轮数开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = agent.review_reflection()

        # 回合开始
        for agent in self.agents:
            # 打印状态
            print(f'\n----****----\nround {self.current_round}, agent {agent.get_name()} starts\n----****----')
            # print(f'current context:\n{agent.get_context()}\n----****----')
            # 智能体对新闻的分析
            pass_list = [
                '大宗商品贸易集团',
                '全球性综合金属生产集团',
                'InstitutionalProfile0',
                'InstitutionalProfile1',
                'InstitutionalProfile2',
                'InstitutionalProfile3',
            ]
            if agent.get_name() not in pass_list:
                # 玩家是普通玩家才会有延迟判定
                got_news = news_delay(news)     # 新闻延迟
            else:
                got_news = news[-1]
            # 专家模型对新闻的分析
            docs = retrieve_query(got_news)
            docs=[]
            rag_info = docs[0] + '\n' + docs[1]
            uttrs_to_be_removed[str(agent.get_id())] += agent.news_analysis_rag(got_news, rag_info)
            # 分析市场信息，生成交易前看多与看空倾向
            for _ in range(5):
                count, judgement_0 = agent.market_info_analysis(retrieved_market_info)
                if count is not None:
                    break
            else:
                print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - market info analysis.")
                return -1

            # 对话成功后
            uttrs_to_be_removed[str(agent.get_id())] += count
            first_judgements[str(agent.get_id())] = judgement_0['judgement']

            # 同步与确认账户信息
            account_info = self.engine.retrieve_account_info(agent.get_id())
            agent.refresh_account_info(account_info)
            uttrs_to_be_removed[str(agent.get_id())] += agent.account_info_confirmation()

        # 出价与交易撮合
        temp_dict_1, succeeded_requests, failed_requests, deals = self.trade_phase_without_expert(
            first_judgements,
            retrieved_market_info
        )

        # 出价与交易撮合过程中出错
        if temp_dict_1 is None:
            return -1

        # 回合结束，账户结算，与本轮策略保存，用于下一回合
        temp_dict_2 = self.settlement_phase()

        # 计数，并删除提示词
        for agent in self.agents:
            key = str(agent.get_id())
            uttrs_to_be_removed[key] += temp_dict_1[key]
            uttrs_to_be_removed[key] += temp_dict_2[key]
            agent.remove_agent_context(
                beginning=-1*uttrs_to_be_removed[key],
            )
            prompt, completion = agent.get_usage()
            print(
                f"\n----------tokens----------\n"
                f"已使用 tokens: prompt - {prompt}; completion - {completion} \n"
                f"--------------------------\n"
            )

        return 0

    def trade_phase(self, first_judgements, market_info):
        """
        在一回合的信息收集环节结束后，开始五轮出价
        :return: 五轮结束后所有成交的和没有成交的订单
        """
        # 交易请求列表
        all_requests = []
        # 撮合后成功的请求，失败的请求，达成的交易单
        succeeded_requests, failed_requests, deals = [], [], []

        # 对话删除计数
        uttrs_to_be_removed = {}
        for agent in self.agents:
            uttrs_to_be_removed[str(agent.get_id())] = 0

        # 5 rounds
        for i in range(5):
            # 发起请求
            new_transactions = []
            last_turn_to_be_removed = {}
            for agent in self.agents:
                last_turn_to_be_removed[str(agent.get_id())] = uttrs_to_be_removed[str(agent.get_id())]
                # 同步账户信息
                account_info = self.engine.retrieve_account_info(agent.get_id())
                agent.refresh_account_info(account_info)

                # 确认是否参与交易
                for _ in range(5):
                    count, anticipation, strategy = agent.transaction_request_phase_1(
                        current_turn=i,
                        attitude=first_judgements[str(agent.get_id())]
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                if anticipation['anticipation'] == '否':
                    # 不参与本轮交易
                    continue

                # 进入第二阶段
                expert_advise = self.expert.advise_to_agent(agent.get_profile(), strategy)   # 请求专家意见，使用 strategy 作为输入
                for _ in range(5):
                    count, transaction_request = agent.transaction_request_phase_2(
                        expert_advise=expert_advise
                    )
                    if count is not None:
                        cnt = count
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 2.")
                    return None, None, None, None

                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                # 基于 transaction_request 生成一系列交易请求单
                if agent.get_name() in ['大宗商品贸易集团', '全球性综合金属生产集团', 'NickelBuyer0']:
                    transactions = generate_transactions(
                        transaction_request,
                        account_info,
                        agent.get_id(),
                        market_info,
                        i,
                        self.security_fund_rate,
                        self.limit,
                        votality=False
                    )
                    new_transactions.extend(transactions)
                else:
                    transactions = generate_transactions(
                        transaction_request,
                        account_info,
                        agent.get_id(),
                        market_info,
                        i,
                        self.security_fund_rate,
                        self.limit,
                        votality=True
                    )
                    new_transactions.extend(transactions)

            # 交易撮合 self.engine
            succeeded_requests, failed_requests, deals = self.engine.deal_making(new_transactions)
            # 更新 all_requests 列表，删除成功的交易
            del all_requests
            all_requests = copy.deepcopy(failed_requests)

            # 撮合成功与失败通知，询问是否撤单
            for agent in self.agents:
                # 筛选响应，转化为通知
                succeeded_filtered, failed_filtered = transactions_response_filter(
                    succeeded_requests,
                    failed_requests,
                    agent.get_id()
                )
                deal_making_result_message = filtered_transactions_formatter(
                    succeeded_filtered,
                    failed_filtered
                )
                # 请求量信息
                buy_amount, buy_price, sell_amount, sell_price = self.engine.get_order_info()
                request_info = (buy_amount, buy_price, sell_amount, sell_price)

                # 生成撤单请求
                for _ in range(5):
                    count, withdraw_requests = agent.transaction_response_and_withdraw(
                        message=deal_making_result_message,
                        request_info=request_info
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                withdraws = update_requests_after_withdraw(
                    failed_filtered=failed_filtered,
                    withdraw_requests=withdraw_requests
                )
                # 引擎将撤单信息同步到数据库
                self.engine.withdraw_requests(withdraw_requests=withdraws)

            # 轮次结束后，删除上一轮次对话上下文
            for agent in self.agents:
                agent.remove_agent_context(
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]),
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]-last_turn_to_be_removed[str(agent.get_id())])
                )
                uttrs_to_be_removed[str(agent.get_id())] -= last_turn_to_be_removed[str(agent.get_id())]

        return uttrs_to_be_removed, succeeded_requests, failed_requests, deals

    def settlement_phase(self):
        """
        交易完成后账户结算，与智能体策略更新
        :return: uttrs_to_be_removed: Dict; None - 结算错误
        """
        # 对话删除计数
        uttrs_to_be_removed = {}
        for agent in self.agents:
            uttrs_to_be_removed[str(agent.get_id())] = 0

        # 账户重新结算，计算最新价格，刷新账户资产，计算平仓问题
        avg_price = self.engine.settlement_of_round()

        if avg_price < 0:
            # 结算错误
            return None

        # 智能体更新账户资产，并保存这一轮次的策略，用于下一轮次的提示词
        for agent in self.agents:
            account_info = self.engine.retrieve_account_info(agent.get_id())
            agent.refresh_account_info(account_info)
            uttrs_to_be_removed[str(agent.get_id())] = agent.current_round_strategy_reflection()

        return uttrs_to_be_removed

    def run_round_without_expert(self, news: tuple[str, str]):
        """
        游戏的第 self.current_round 回合，出现新闻 news，专家默认回复无信息量信息
        :param news: （上一回合新闻，本回合新闻）
        :return: 0
        """

        # 同步回合信息
        self.current_round += 1
        assert self.engine.round_end() == self.current_round, "Engine round number is out of sync"
        for agent in self.agents:
            assert agent.round_end() == self.current_round, "agent round number is out of sync"

        if self.current_round == self.contract_round + 1:
            return 0

        # 追加资金
        for agent in self.agents:
            self.engine.fund_supplement(agent.get_id(), agent.get_fund_supplement())

        # retrieve info
        retrieved_market_info = self.engine.retrieve_market_info()
        # analyze news, market info
        first_judgements = {}   # 本轮的最初态度

        # 对话删除计数
        uttrs_to_be_removed = {}
        if self.current_round == 1:
            # 第一回合，没有上一轮策略的对话，从零开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = 0
        else:
            # 包含上一轮的策略，从确认上一轮策略使用的对话轮数开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = agent.review_reflection()

        # 回合开始
        for agent in self.agents:
            # 打印状态
            print(f'\n----****----\nround {self.current_round}, agent {agent.get_name()} starts\n----****----')
            # print(f'current context:\n{agent.get_context()}\n----****----')
            # 智能体对新闻的分析
            pass_list = [
                '大宗商品贸易集团',
                '全球性综合金属生产集团',
                'InstitutionalProfile0',
                'InstitutionalProfile1',
                'InstitutionalProfile2',
                'InstitutionalProfile3',
            ]
            if agent.get_name() not in pass_list:
                # 玩家是普通玩家才会有延迟判定
                got_news = news_delay(news)     # 新闻延迟
            else:
                got_news = news[-1]
            # 专家模型对新闻的分析
            expert_observation = self.expert.without_expert()
            uttrs_to_be_removed[str(agent.get_id())] += agent.news_analysis(got_news, expert_observation)
            # 分析市场信息，生成交易前看多与看空倾向
            for _ in range(5):
                count, judgement_0 = agent.market_info_analysis(retrieved_market_info)
                if count is not None:
                    break
            else:
                print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - market info analysis.")
                return -1

            # 对话成功后
            uttrs_to_be_removed[str(agent.get_id())] += count
            first_judgements[str(agent.get_id())] = judgement_0['judgement']

            # 同步与确认账户信息
            account_info = self.engine.retrieve_account_info(agent.get_id())
            agent.refresh_account_info(account_info)
            uttrs_to_be_removed[str(agent.get_id())] += agent.account_info_confirmation()

        # 出价与交易撮合
        temp_dict_1, succeeded_requests, failed_requests, deals = self.trade_phase_without_expert(
            first_judgements,
            retrieved_market_info
        )

        # 出价与交易撮合过程中出错
        if temp_dict_1 is None:
            return -1

        # 回合结束，账户结算，与本轮策略保存，用于下一回合
        temp_dict_2 = self.settlement_phase()

        # 计数，并删除提示词
        for agent in self.agents:
            key = str(agent.get_id())
            uttrs_to_be_removed[key] += temp_dict_1[key]
            uttrs_to_be_removed[key] += temp_dict_2[key]
            agent.remove_agent_context(
                beginning=-1*uttrs_to_be_removed[key],
            )
            prompt, completion = agent.get_usage()
            print(
                f"\n----------tokens----------\n"
                f"已使用 tokens: prompt - {prompt}; completion - {completion} \n"
                f"--------------------------\n"
            )

        return 0

    def trade_phase_without_expert(self, first_judgements, market_info):
        """
        在一回合的信息收集环节结束后，开始五轮出价，专家默认回复无信息量信息
        :return: 五轮结束后所有成交的和没有成交的订单
        """
        # 交易请求列表
        all_requests = []
        # 撮合后成功的请求，失败的请求，达成的交易单
        succeeded_requests, failed_requests, deals = [], [], []

        # 对话删除计数
        uttrs_to_be_removed = {}
        for agent in self.agents:
            uttrs_to_be_removed[str(agent.get_id())] = 0

        # 2 rounds
        for i in range(2):
            # 发起请求
            new_transactions = []
            last_turn_to_be_removed = {}
            for agent in self.agents:
                last_turn_to_be_removed[str(agent.get_id())] = uttrs_to_be_removed[str(agent.get_id())]
                # 同步账户信息
                account_info = self.engine.retrieve_account_info(agent.get_id())
                agent.refresh_account_info(account_info)

                # 确认是否参与交易
                for _ in range(5):
                    count, anticipation, strategy = agent.transaction_request_phase_1(
                        current_turn=i,
                        attitude=first_judgements[str(agent.get_id())]
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                if anticipation['anticipation'] == '否':
                    # 不参与本轮交易
                    continue

                # 进入第二阶段
                expert_advise = self.expert.without_expert()   # 请求专家意见，使用 strategy 作为输入
                for _ in range(5):
                    count, transaction_request = agent.transaction_request_phase_2(
                        expert_advise=expert_advise
                    )
                    if count is not None:
                        cnt = count
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 2.")
                    return None, None, None, None

                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                # 基于 transaction_request 生成一系列交易请求单
                if agent.get_name() in ['大宗商品贸易集团', '全球性综合金属生产集团', 'NickelBuyer0']:
                    transactions = generate_transactions(
                        transaction_request,
                        account_info,
                        agent.get_id(),
                        market_info,
                        i,
                        self.security_fund_rate,
                        self.limit,
                        votality=False
                    )
                    new_transactions.extend(transactions)
                else:
                    transactions = generate_transactions(
                        transaction_request,
                        account_info,
                        agent.get_id(),
                        market_info,
                        i,
                        self.security_fund_rate,
                        self.limit,
                        votality=True
                    )
                    new_transactions.extend(transactions)

            # 交易撮合 self.engine
            succeeded_requests, failed_requests, deals = self.engine.deal_making(new_transactions)
            # 更新 all_requests 列表，删除成功的交易
            del all_requests
            all_requests = copy.deepcopy(failed_requests)

            # 撮合成功与失败通知，询问是否撤单
            for agent in self.agents:
                # 筛选响应，转化为通知
                succeeded_filtered, failed_filtered = transactions_response_filter(
                    succeeded_requests,
                    failed_requests,
                    agent.get_id()
                )
                deal_making_result_message = filtered_transactions_formatter(
                    succeeded_filtered,
                    failed_filtered
                )
                # 请求量信息
                buy_amount, buy_price, sell_amount, sell_price = self.engine.get_order_info()
                request_info = (buy_amount, buy_price, sell_amount, sell_price)

                # 生成撤单请求
                for _ in range(5):
                    count, withdraw_requests = agent.transaction_response_and_withdraw(
                        message=deal_making_result_message,
                        request_info=request_info
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                withdraws = update_requests_after_withdraw(
                    failed_filtered=failed_filtered,
                    withdraw_requests=withdraw_requests
                )
                # 引擎将撤单信息同步到数据库
                self.engine.withdraw_requests(withdraw_requests=withdraws)

            # 轮次结束后，删除上一轮次对话上下文
            for agent in self.agents:
                agent.remove_agent_context(
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]),
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]-last_turn_to_be_removed[str(agent.get_id())])
                )
                uttrs_to_be_removed[str(agent.get_id())] -= last_turn_to_be_removed[str(agent.get_id())]

        return uttrs_to_be_removed, succeeded_requests, failed_requests, deals

    def run_round_without_generator(self, news: tuple[str, str]):
        """
            游戏的第 self.current_round 回合，出现新闻 news，有专家，但无生成器
            :param news: （上一回合新闻，本回合新闻）
            :return: 0
            """

        # 同步回合信息
        self.current_round += 1
        assert self.engine.round_end() == self.current_round, "Engine round number is out of sync"
        for agent in self.agents:
            assert agent.round_end() == self.current_round, "agent round number is out of sync"

        if self.current_round == self.contract_round + 1:
            return 0

        # 追加资金
        for agent in self.agents:
            self.engine.fund_supplement(agent.get_id(), agent.get_fund_supplement())

        # retrieve info
        retrieved_market_info = self.engine.retrieve_market_info()
        # analyze news, market info
        first_judgements = {}   # 本轮的最初态度

        # 对话删除计数
        uttrs_to_be_removed = {}
        if self.current_round == 1:
            # 第一回合，没有上一轮策略的对话，从零开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = 0
        else:
            # 包含上一轮的策略，从确认上一轮策略使用的对话轮数开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = agent.review_reflection()

        # 回合开始
        for agent in self.agents:
            # 打印状态
            print(f'\n----****----\nround {self.current_round}, agent {agent.get_name()} starts\n----****----')
            # print(f'current context:\n{agent.get_context()}\n----****----')
            # 智能体对新闻的分析
            pass_list = [
                '大宗商品贸易集团',
                '全球性综合金属生产集团',
                'InstitutionalProfile0',
                'InstitutionalProfile1',
                'InstitutionalProfile2',
                'InstitutionalProfile3',
            ]
            if agent.get_name() not in pass_list:
                # 玩家是普通玩家才会有延迟判定
                got_news = news_delay(news)     # 新闻延迟
            else:
                got_news = news[-1]
            # 专家模型对新闻的分析
            expert_observation = self.expert.news_analysis(got_news)
            uttrs_to_be_removed[str(agent.get_id())] += agent.news_analysis(got_news, expert_observation)
            # 分析市场信息，生成交易前看多与看空倾向
            for _ in range(5):
                count, judgement_0 = agent.market_info_analysis(retrieved_market_info)
                if count is not None:
                    break
            else:
                print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - market info analysis.")
                return -1

            # 对话成功后
            uttrs_to_be_removed[str(agent.get_id())] += count
            first_judgements[str(agent.get_id())] = judgement_0['judgement']

            # 同步与确认账户信息
            account_info = self.engine.retrieve_account_info(agent.get_id())
            agent.refresh_account_info(account_info)
            uttrs_to_be_removed[str(agent.get_id())] += agent.account_info_confirmation()


        # 出价与交易撮合
        temp_dict_1, succeeded_requests, failed_requests, deals = self.trade_phase_without_generator(
            first_judgements,
            retrieved_market_info
        )

        # 出价与交易撮合过程中出错
        if temp_dict_1 is None:
            return -1

        # 回合结束，账户结算，与本轮策略保存，用于下一回合
        temp_dict_2 = self.settlement_phase()

        # 计数，并删除提示词
        for agent in self.agents:
            key = str(agent.get_id())
            uttrs_to_be_removed[key] += temp_dict_1[key]
            uttrs_to_be_removed[key] += temp_dict_2[key]
            agent.remove_agent_context(
                beginning=-1*uttrs_to_be_removed[key],
            )
            prompt, completion = agent.get_usage()
            print(
                f"\n----------tokens----------\n"
                f"已使用 tokens: prompt - {prompt}; completion - {completion} \n"
                f"--------------------------\n"
            )

        return 0

    def trade_phase_without_generator(self, first_judgements, market_info):
        """
        在一回合的信息收集环节结束后，开始五轮出价，有专家，但无生成器
        :return: 五轮结束后所有成交的和没有成交的订单
        """
        # 交易请求列表
        all_requests = []
        # 撮合后成功的请求，失败的请求，达成的交易单
        succeeded_requests, failed_requests, deals = [], [], []

        # 对话删除计数
        uttrs_to_be_removed = {}
        for agent in self.agents:
            uttrs_to_be_removed[str(agent.get_id())] = 0

        # 5 rounds
        for i in range(5):
            # 发起请求
            new_transactions = []
            last_turn_to_be_removed = {}
            for agent in self.agents:
                last_turn_to_be_removed[str(agent.get_id())] = uttrs_to_be_removed[str(agent.get_id())]
                # 同步账户信息
                account_info = self.engine.retrieve_account_info(agent.get_id())
                agent.refresh_account_info(account_info)

                # 确认是否参与交易
                for _ in range(5):
                    count, anticipation, strategy = agent.transaction_request_phase_1_without_generator(
                        current_turn=i,
                        attitude=first_judgements[str(agent.get_id())]
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                if anticipation['anticipation'] == '否':
                    # 不参与本轮交易
                    continue

                # 进入第二阶段
                expert_advise = self.expert.advise_to_agent(agent.get_profile(), strategy)   # 请求专家意见，使用 strategy 作为输入
                for _ in range(5):
                    count, transaction_request = agent.transaction_request_phase_2_without_generator(
                        expert_advise=expert_advise
                    )
                    if count is not None:
                        cnt = count
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 2.")
                    return None, None, None, None

                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                # 基于 transaction_request 生成一系列交易请求单
                transactions = generate_transactions_without_generator(
                    transaction_request,
                    account_info,
                    agent.get_id(),
                    market_info,
                    i,
                    self.security_fund_rate,
                    self.limit
                )
                new_transactions.extend(transactions)

            # 交易撮合 self.engine
            succeeded_requests, failed_requests, deals = self.engine.deal_making(new_transactions)
            # 更新 all_requests 列表，删除成功的交易
            del all_requests
            all_requests = copy.deepcopy(failed_requests)

            # 撮合成功与失败通知，询问是否撤单
            for agent in self.agents:
                # 筛选响应，转化为通知
                succeeded_filtered, failed_filtered = transactions_response_filter(
                    succeeded_requests,
                    failed_requests,
                    agent.get_id()
                )
                deal_making_result_message = filtered_transactions_formatter(
                    succeeded_filtered,
                    failed_filtered
                )
                # 请求量信息
                buy_amount, buy_price, sell_amount, sell_price = self.engine.get_order_info()
                request_info = (buy_amount, buy_price, sell_amount, sell_price)

                # 生成撤单请求
                for _ in range(5):
                    count, withdraw_requests = agent.transaction_response_and_withdraw_without_generator(
                        message=deal_making_result_message,
                        request_info=request_info
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                withdraws = update_requests_after_withdraw_without_generator(
                    failed_filtered=failed_filtered,
                    withdraw_requests=withdraw_requests
                )
                # 引擎将撤单信息同步到数据库
                self.engine.withdraw_requests(withdraw_requests=withdraws)

            # 轮次结束后，删除上一轮次对话上下文
            for agent in self.agents:
                agent.remove_agent_context(
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]),
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]-last_turn_to_be_removed[str(agent.get_id())])
                )
                uttrs_to_be_removed[str(agent.get_id())] -= last_turn_to_be_removed[str(agent.get_id())]

        return uttrs_to_be_removed, succeeded_requests, failed_requests, deals

    def run_round_without_expert_and_generator(self, news: tuple[str, str]):
        """
            游戏的第 self.current_round 回合，出现新闻 news，无专家，且无生成器
            :param news: （上一回合新闻，本回合新闻）
            :return: 0
            """

        # 同步回合信息
        self.current_round += 1
        assert self.engine.round_end() == self.current_round, "Engine round number is out of sync"
        for agent in self.agents:
            assert agent.round_end() == self.current_round, "agent round number is out of sync"

        if self.current_round == self.contract_round + 1:
            return 0

        # 追加资金
        for agent in self.agents:
            self.engine.fund_supplement(agent.get_id(), agent.get_fund_supplement())

        # retrieve info
        retrieved_market_info = self.engine.retrieve_market_info()
        # analyze news, market info
        first_judgements = {}   # 本轮的最初态度

        # 对话删除计数
        uttrs_to_be_removed = {}
        if self.current_round == 1:
            # 第一回合，没有上一轮策略的对话，从零开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = 0
        else:
            # 包含上一轮的策略，从确认上一轮策略使用的对话轮数开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = agent.review_reflection()

        # 回合开始
        for agent in self.agents:
            # 打印状态
            print(f'\n----****----\nround {self.current_round}, agent {agent.get_name()} starts\n----****----')
            # print(f'current context:\n{agent.get_context()}\n----****----')
            # 智能体对新闻的分析
            pass_list = [
                '大宗商品贸易集团',
                '全球性综合金属生产集团',
                'InstitutionalProfile0',
                'InstitutionalProfile1',
                'InstitutionalProfile2',
                'InstitutionalProfile3',
            ]
            if agent.get_name() not in pass_list:
                # 玩家是普通玩家才会有延迟判定
                got_news = news_delay(news)     # 新闻延迟
            else:
                got_news = news[-1]
            # 专家模型对新闻的分析
            expert_observation = self.expert.without_expert()
            uttrs_to_be_removed[str(agent.get_id())] += agent.news_analysis(got_news, expert_observation)
            # 分析市场信息，生成交易前看多与看空倾向
            for _ in range(5):
                count, judgement_0 = agent.market_info_analysis(retrieved_market_info)
                if count is not None:
                    break
            else:
                print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - market info analysis.")
                return -1

            # 对话成功后
            uttrs_to_be_removed[str(agent.get_id())] += count
            first_judgements[str(agent.get_id())] = judgement_0['judgement']

            # 同步与确认账户信息
            account_info = self.engine.retrieve_account_info(agent.get_id())
            agent.refresh_account_info(account_info)
            uttrs_to_be_removed[str(agent.get_id())] += agent.account_info_confirmation()

        # 出价与交易撮合
        temp_dict_1, succeeded_requests, failed_requests, deals = self.trade_phase_without_generator(
            first_judgements,
            retrieved_market_info
        )

        # 出价与交易撮合过程中出错
        if temp_dict_1 is None:
            return -1

        # 回合结束，账户结算，与本轮策略保存，用于下一回合
        temp_dict_2 = self.settlement_phase()

        # 计数，并删除提示词
        for agent in self.agents:
            key = str(agent.get_id())
            uttrs_to_be_removed[key] += temp_dict_1[key]
            uttrs_to_be_removed[key] += temp_dict_2[key]
            agent.remove_agent_context(
                beginning=-1*uttrs_to_be_removed[key],
            )
            prompt, completion = agent.get_usage()
            print(
                f"\n----------tokens----------\n"
                f"已使用 tokens: prompt - {prompt}; completion - {completion} \n"
                f"--------------------------\n"
            )

        return 0

    def trade_phase_without_expert_and_generator(self, first_judgements, market_info):
        """
        在一回合的信息收集环节结束后，开始五轮出价，无专家，且无生成器
        :return: 五轮结束后所有成交的和没有成交的订单
        """
        # 交易请求列表
        all_requests = []
        # 撮合后成功的请求，失败的请求，达成的交易单
        succeeded_requests, failed_requests, deals = [], [], []

        # 对话删除计数
        uttrs_to_be_removed = {}
        for agent in self.agents:
            uttrs_to_be_removed[str(agent.get_id())] = 0

        # 5 rounds
        for i in range(5):
            # 发起请求
            new_transactions = []
            last_turn_to_be_removed = {}
            for agent in self.agents:
                last_turn_to_be_removed[str(agent.get_id())] = uttrs_to_be_removed[str(agent.get_id())]
                # 同步账户信息
                account_info = self.engine.retrieve_account_info(agent.get_id())
                agent.refresh_account_info(account_info)

                # 确认是否参与交易
                for _ in range(5):
                    count, anticipation, strategy = agent.transaction_request_phase_1_without_generator(
                        current_turn=i,
                        attitude=first_judgements[str(agent.get_id())]
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                if anticipation['anticipation'] == '否':
                    # 不参与本轮交易
                    continue

                # 进入第二阶段
                expert_advise = self.expert.without_expert()   # 请求专家意见，使用 strategy 作为输入
                for _ in range(5):
                    count, transaction_request = agent.transaction_request_phase_2_without_generator(
                        expert_advise=expert_advise
                    )
                    if count is not None:
                        cnt = count
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 2.")
                    return None, None, None, None

                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                # 基于 transaction_request 生成一系列交易请求单
                transactions = generate_transactions_without_generator(
                    transaction_request,
                    account_info,
                    agent.get_id(),
                    market_info,
                    i,
                    self.security_fund_rate,
                    self.limit
                )
                new_transactions.extend(transactions)

            # 交易撮合 self.engine
            succeeded_requests, failed_requests, deals = self.engine.deal_making(new_transactions)
            # 更新 all_requests 列表，删除成功的交易
            del all_requests
            all_requests = copy.deepcopy(failed_requests)

            # 撮合成功与失败通知，询问是否撤单
            for agent in self.agents:
                # 筛选响应，转化为通知
                succeeded_filtered, failed_filtered = transactions_response_filter(
                    succeeded_requests,
                    failed_requests,
                    agent.get_id()
                )
                deal_making_result_message = filtered_transactions_formatter(
                    succeeded_filtered,
                    failed_filtered
                )
                # 请求量信息
                buy_amount, buy_price, sell_amount, sell_price = self.engine.get_order_info()
                request_info = (buy_amount, buy_price, sell_amount, sell_price)

                # 生成撤单请求
                for _ in range(5):
                    count, withdraw_requests = agent.transaction_response_and_withdraw_without_generator(
                        message=deal_making_result_message,
                        request_info=request_info
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                withdraws = update_requests_after_withdraw_without_generator(
                    failed_filtered=failed_filtered,
                    withdraw_requests=withdraw_requests
                )
                # 引擎将撤单信息同步到数据库
                self.engine.withdraw_requests(withdraw_requests=withdraws)

            # 轮次结束后，删除上一轮次对话上下文
            for agent in self.agents:
                agent.remove_agent_context(
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]),
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]-last_turn_to_be_removed[str(agent.get_id())])
                )
                uttrs_to_be_removed[str(agent.get_id())] -= last_turn_to_be_removed[str(agent.get_id())]

        return uttrs_to_be_removed, succeeded_requests, failed_requests, deals

    def run_round_new(self, news: tuple[str, str], price_file, amount_file):
        """
        游戏的第 self.current_round 回合，出现新闻 news
        :param news: （上一回合新闻，本回合新闻）
        :return: 0
        """

        # 同步回合信息
        self.current_round += 1
        assert self.engine.round_end() == self.current_round, "Engine round number is out of sync"
        for agent in self.agents:
            assert agent.round_end() == self.current_round, "agent round number is out of sync"

        if self.current_round == self.contract_round + 1:
            return 0

        # 追加资金
        for agent in self.agents:
            self.engine.fund_supplement(agent.get_id(), agent.get_fund_supplement())

        # retrieve info
        retrieved_market_info = self.engine.retrieve_market_info()
        # analyze news, market info
        first_judgements = {}   # 本轮的最初态度

        # 对话删除计数
        uttrs_to_be_removed = {}
        if self.current_round == 1:
            # 第一回合，没有上一轮策略的对话，从零开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = 0
        else:
            # 包含上一轮的策略，从确认上一轮策略使用的对话轮数开始计数
            for agent in self.agents:
                uttrs_to_be_removed[str(agent.get_id())] = agent.review_reflection()

        # 回合开始
        for agent in self.agents:
            # 打印状态
            print(f'\n----****----\nround {self.current_round}, agent {agent.get_name()} starts\n----****----')
            # print(f'current context:\n{agent.get_context()}\n----****----')
            # 智能体对新闻的分析
            pass_list = [
                '大宗商品贸易集团',
                '全球性综合金属生产集团',
                'InstitutionalProfile0',
                'InstitutionalProfile1',
                'InstitutionalProfile2',
                'InstitutionalProfile3',
            ]
            if agent.get_name() not in pass_list:
                # 玩家是普通玩家才会有延迟判定
                got_news = news_delay(news)     # 新闻延迟
            else:
                got_news = news[-1]
            # 专家模型对新闻的分析
            expert_observation = self.expert.news_analysis(got_news)
            uttrs_to_be_removed[str(agent.get_id())] += agent.news_analysis(got_news, expert_observation)
            # 分析市场信息，生成交易前看多与看空倾向
            for _ in range(5):
                count, judgement_0 = agent.market_info_analysis(retrieved_market_info)
                if count is not None:
                    break
            else:
                print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - market info analysis.")
                return -1

            # 对话成功后
            uttrs_to_be_removed[str(agent.get_id())] += count
            first_judgements[str(agent.get_id())] = judgement_0['judgement']

            # 同步与确认账户信息
            account_info = self.engine.retrieve_account_info(agent.get_id())
            agent.refresh_account_info(account_info)
            uttrs_to_be_removed[str(agent.get_id())] += agent.account_info_confirmation()

        # 出价与交易撮合
        temp_dict_1, succeeded_requests, failed_requests, deals = self.trade_phase_new(
            first_judgements,
            retrieved_market_info,
            price_file,
            amount_file
        )

        # 出价与交易撮合过程中出错
        if temp_dict_1 is None:
            return -1

        # 回合结束，账户结算，与本轮策略保存，用于下一回合
        temp_dict_2 = self.settlement_phase()

        # 计数，并删除提示词
        for agent in self.agents:
            key = str(agent.get_id())
            uttrs_to_be_removed[key] += temp_dict_1[key]
            uttrs_to_be_removed[key] += temp_dict_2[key]
            agent.remove_agent_context(
                beginning=-1*uttrs_to_be_removed[key],
            )
            prompt, completion = agent.get_usage()
            print(
                f"\n----------tokens----------\n"
                f"已使用 tokens: prompt - {prompt}; completion - {completion} \n"
                f"--------------------------\n"
            )

        return 0

    def trade_phase_new(self, first_judgements, market_info, price_file, amount_file):
        """
        在一回合的信息收集环节结束后，开始五轮出价
        :return: 五轮结束后所有成交的和没有成交的订单
        """
        # 交易请求列表
        all_requests = []
        # 撮合后成功的请求，失败的请求，达成的交易单
        succeeded_requests, failed_requests, deals = [], [], []

        # 对话删除计数
        uttrs_to_be_removed = {}
        for agent in self.agents:
            uttrs_to_be_removed[str(agent.get_id())] = 0

        # 2 rounds
        for i in range(2):
            # 发起请求
            new_transactions = []
            last_turn_to_be_removed = {}
            for agent in self.agents:
                last_turn_to_be_removed[str(agent.get_id())] = uttrs_to_be_removed[str(agent.get_id())]
                # 同步账户信息
                account_info = self.engine.retrieve_account_info(agent.get_id())
                agent.refresh_account_info(account_info)

                # 确认是否参与交易
                for _ in range(5):
                    count, anticipation, strategy = agent.transaction_request_phase_1(
                        current_turn=i,
                        attitude=first_judgements[str(agent.get_id())]
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                if anticipation['anticipation'] == '否':
                    # 不参与本轮交易
                    continue

                # 进入第二阶段
                expert_advise = self.expert.advise_to_agent(agent.get_profile(), strategy)   # 请求专家意见，使用 strategy 作为输入
                for _ in range(5):
                    count, transaction_request = agent.transaction_request_phase_2(
                        expert_advise=expert_advise
                    )
                    if count is not None:
                        cnt = count
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 2.")
                    return None, None, None, None

                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                # 基于 transaction_request 生成一系列交易请求单
                transactions = generate_transactions_new(
                    price_file,
                    amount_file,
                    transaction_request,
                    account_info,
                    agent.get_id(),
                    market_info,
                    i,
                    self.security_fund_rate,
                    self.limit,
                    votality=True
                )
                new_transactions.extend(transactions)

            # 交易撮合 self.engine
            succeeded_requests, failed_requests, deals = self.engine.deal_making(new_transactions)
            # 更新 all_requests 列表，删除成功的交易
            del all_requests
            all_requests = copy.deepcopy(failed_requests)

            # 撮合成功与失败通知，询问是否撤单
            for agent in self.agents:
                # 筛选响应，转化为通知
                succeeded_filtered, failed_filtered = transactions_response_filter(
                    succeeded_requests,
                    failed_requests,
                    agent.get_id()
                )
                deal_making_result_message = filtered_transactions_formatter(
                    succeeded_filtered,
                    failed_filtered
                )
                # 请求量信息
                buy_amount, buy_price, sell_amount, sell_price = self.engine.get_order_info()
                request_info = (buy_amount, buy_price, sell_amount, sell_price)

                # 生成撤单请求
                for _ in range(5):
                    count, withdraw_requests = agent.transaction_response_and_withdraw(
                        message=deal_making_result_message,
                        request_info=request_info
                    )
                    if count is not None:
                        break
                else:
                    print(f"failed in 5 times: {agent.get_name()} in round {self.current_round}. task - transaction request 1.")
                    return None, None, None, None


                # 对话成功后
                uttrs_to_be_removed[str(agent.get_id())] += count

                withdraws = update_requests_after_withdraw(
                    failed_filtered=failed_filtered,
                    withdraw_requests=withdraw_requests
                )
                # 引擎将撤单信息同步到数据库
                self.engine.withdraw_requests(withdraw_requests=withdraws)

            # 轮次结束后，删除上一轮次对话上下文
            for agent in self.agents:
                agent.remove_agent_context(
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]),
                    -1 * (uttrs_to_be_removed[str(agent.get_id())]-last_turn_to_be_removed[str(agent.get_id())])
                )
                uttrs_to_be_removed[str(agent.get_id())] -= last_turn_to_be_removed[str(agent.get_id())]

        return uttrs_to_be_removed, succeeded_requests, failed_requests, deals