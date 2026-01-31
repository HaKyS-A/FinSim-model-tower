"""引擎类，连接数据库，计算等"""
from decimal import Decimal

try:
    import config
except:
    import Engine.config as config
try:
    from dbmanager import DatabaseManager
except:
    from .dbmanager import DatabaseManager

error_file = open("Error.txt", "w", encoding='utf-8')


class Engine:
    """引擎类"""

    def __init__(self):
        self.round = 0
        self.db = None  # 修改，原来的self.cursor变成dbmanager的内置变量了，这里直接通过self.db实现对数据库的所有操作
        self.futures = []
        # 镍编号
        self.Ni_id = 1
        # 最晚交割回合
        self.contract_round = 0
        # 上一笔交易的成交价(初始化为镍期货初始价格)，用于确定撮合成交时的交易价格
        self.last_price = Decimal(0)
        # 保证金比例
        self.margin_rate = Decimal(0)
        # 价格限制
        self.price_limit = Decimal(0)
        # 上一轮交易收盘价，用于保证价格限制
        self.last_round_price = Decimal(0)
        self.super_user_id = 999  # 超级用户的id，被动参与交易

    def sync_system_setting(self, security_fund_rate, limit, contract_round):
        """同步系统设定，security_fund_rate & limit & contract_round"""
        self.margin_rate = Decimal(security_fund_rate / 100).quantize(Decimal('0.0000000'))
        self.price_limit = Decimal(limit / 100).quantize(Decimal('0.0000000'))
        self.contract_round = contract_round

    def create_super_user(self, funds: Decimal = Decimal(999999)):
        funds = Decimal(funds).quantize(Decimal('0.0000000'))
        player_info = {'`agent_id`': self.super_user_id, '`agent_name`': "SuperUser", '`agent_type`': "major player",
                       '`init_fund`': funds, '`agent_info`': "Hey, I'm helpful superuser!"}
        # 插入智能体信息表
        status = self.db.agent_insert(player_info)
        if status == -1:
            print("超级用户的信息录入失败，进程意外结束")
            exit(-1)
        # print(f"玩家{player_id}信息录入成功，status={status}")
        # 第0轮，也需要插入超级用户的记录表
        agent_record_info = {'agent_id': self.super_user_id, 'round': self.round, 'current_funds': funds,
                             'available_funds': funds, 'security_funds': 0, 'profit_loss': 0}
        self.db.agent_record_insert(agent_record_info)
        if status == -1:
            print("超级用户的记录信息插入失败，进程意外结束")
            exit(-1)

    def engine_init(self, db_name, players: list, initial_futures_price: float, initial_actuals_price: float,
                    Ni_inventory: float):
        """
        创建新数据库，初始化各表单，玩家信息，要求为每个玩家赋予id
        :param db_name: 数据库名称
        :param players: 玩家列表
        :param initial_futures_price: 初始价格，镍期货（有修改）
        ----新增
        :param initial_actuals_price:初始价格，镍现货
        :param Ni_inventory:镍现货的库存
        需要在player中新增get_capital方法（获取初始资金）和get_info方法获取个人资料
        ------
        :return: 0 - 成功结束
        """
        # 相关变量初始化
        self.contract_round = self.contract_round
        self.last_price = Decimal(initial_futures_price).quantize(Decimal('0.0000000'))
        self.margin_rate = Decimal(self.margin_rate)
        self.price_limit = Decimal(self.price_limit)
        self.last_round_price = Decimal(initial_futures_price).quantize(Decimal('0.0000000'))

        # 连接数据库
        self.db = DatabaseManager(**config.connect_config)
        # conn = self.db.get_connect()

        # 创建数据库
        db_find_sql = f"DROP DATABASE IF EXISTS {db_name}"
        status = self.db.execute_sql(db_find_sql)
        if status is None:
            print(f"DROP DATABASE IF EXISTS {db_name}失败")
            exit(-1)
        print(f"数据库{db_name}存在，删除数据库完成")
        self.db.create_db(db_name)

        # 选择数据库
        self.db.select_db(db_name)

        # 创建表单
        self.db.create_table('agent', config.agent_field)  # 智能体表
        self.db.create_table('futures', config.futures_field)  # 期货合约表
        self.db.create_table('order', config.order_field)  # 下单信息表
        self.db.create_table('agent_record', config.agent_record_field)  # 智能体记录表
        self.db.create_table('futures_record', config.futures_record_field)  # 期货合约记录表
        self.db.create_table('actuals', config.actuals_field)  # 现货表
        self.db.create_table('deal_record', config.deal_record_field)  # 订单成交记录表

        # 加入期货信息
        # 目前为镍，包含编号、名称、品种、初始价格、限额、保证金比例、最晚交割回合，传入insert的是{"":""}，需要指定的通过变量表示
        # 目前将镍期货的类型设置为“metal”（金属）
        Nickle_inf = {
            "futures_id": self.Ni_id,
            "futures_name": 'Nickle',
            "commodity": 'metal', "init_price": initial_futures_price,
            "price_limit": self.price_limit,
            "margin_rate": self.margin_rate,
            "contract_round": self.contract_round
        }
        status = self.db.futures_insert(Nickle_inf)
        if status == -1:
            print("镍期货信息插入失败，进程意外结束")
            exit(-1)
        # print(f"镍期货信息加入成功,status={status}")
        # 统一处理，所以将这个信息加入期货价格记录表【round=0对应初始状态】
        Nickle_record = {
            'futures_id': self.Ni_id,
            'round': self.round,
            'settlement_price': initial_futures_price
        }
        status = self.db.futures_record_insert(Nickle_record)
        if status == -1:
            print("镍期货信息记录插入失败，进程意外结束")
            exit(-1)
        # print(f"镍期货信息记录加入成功,status={status}")

        # 加入玩家信息
        player_id = 0  # 玩家编号，从0开始
        for player in players:
            name = player.get_name()  # 姓名
            # 根据名称，和profile等在数据库中添加玩家，有需要的数据写在这个注释这里
            # 类型，大宗/散户
            if name in ['Glencore', 'QingShan']:
                agent_type = 'major player'
            else:
                agent_type = 'retail investor'
            init_fund = Decimal(player.get_capital()).quantize(Decimal('0.0000000'))  # 获取初始资金
            agent_info = player.get_profile()  # 获取资料
            player_info = {'`agent_id`': player_id, '`agent_name`': name, '`agent_type`': agent_type,
                           '`init_fund`': init_fund, '`agent_info`': agent_info}
            # 插入智能体信息表
            status = self.db.agent_insert(player_info)
            if status == -1:
                print(f"玩家{player_id}信息录入失败，进程意外结束")
                exit(-1)
            # print(f"玩家{player_id}信息录入成功，status={status}")
            # 第0轮，也需要插入智能体记录表
            agent_record_info = {'agent_id': player_id, 'round': self.round, 'current_funds': init_fund,
                                 'available_funds': init_fund, 'security_funds': 0, 'profit_loss': 0}
            self.db.agent_record_insert(agent_record_info)
            if status == -1:
                print(f"玩家{player_id}记录信息插入失败，进程意外结束")
                exit(-1)
            # print(f"玩家{player_id}记录信息录入成功,status={status}")
            # 更新玩家信息
            player.set_id(player_id)
            player_id += 1

        self.create_super_user()  # 创建超级用户，方便后续插入模拟开始前的期货购买情况

        # 创建镍现货，初始价格等，其它信息有需要在此处添加
        Nickle_acutal = {
            "actuals_id": self.Ni_id,
            "actuals_name": 'Nickle',
            "current_price": initial_actuals_price,
            "current_round": self.round,
            "inventory": Ni_inventory
        }
        self.db.actuals_insert(Nickle_acutal)
        if status == -1:
            print("镍现货信息插入失败，进程意外结束")
            exit(-1)
        # print(f"镍现货信息加入成功,status={status}")

        return 0

    def _order_info_insert(self, agent_id, order_type, order_price, order_lots, order_round, order_num: int = 0,
                           remain_lots: Decimal = Decimal(0), order_status: str = 'done'):
        '''
        辅助函数，插入订单信息到order表中
        返回插入订单编号，-1说明无效
        '''
        order_lots = Decimal(order_lots).quantize(Decimal('0.0000000'))
        if order_lots == Decimal(0).quantize(Decimal('0.0000000')):
            return -1
        order_inf = {
            'agent_id': agent_id,
            'futures_id': self.Ni_id,
            'order_type': order_type,
            'order_price': order_price,
            'order_lots': order_lots,
            'remain_lots': remain_lots,
            'order_round': order_round,
            'order_num': order_num,
            'order_status': order_status
        }
        status = self.db.order_insert(order_inf)
        if status == -1:
            print(f"玩家{agent_id}的第{order_round}轮交易插入失败，进程意外退出")
            exit(-1)
        return status

    def original_position_init(self, positions: list, before: int = 0, before_before: int = -1):
        '''
        模拟开始前的持仓信息初始化，默认所有订单的交易方均为超级用户，默认价格为初始价格设置（self.last_price)
        :param positions:list(list),[[player_id,模拟前两轮（-1轮）的买单量，模拟前两轮（-1轮）的卖单量，模拟前一轮（0轮）的买单量，模拟前一轮（0轮）的卖单量],...]
        :param before(_before)：模拟前一（两)轮的round编号
        '''
        if len(positions) == 0:
            return
        buy_cnt0 = sum(row[1] for row in positions)  # 前两轮的总买单量
        sell_cnt0 = sum(row[2] for row in positions)  # 前两轮的总卖单量
        buy_cnt1 = sum(row[3] for row in positions)  # 前一轮的总买单量
        sell_cnt1 = sum(row[4] for row in positions)  # 前一轮的总卖单量
        # 先插入超级用户（交易方的订单信息）
        super_sell0 = self._order_info_insert(agent_id=self.super_user_id, order_type='sell',
                                              order_price=self.last_price, order_lots=Decimal(buy_cnt0),
                                              order_round=before_before)
        super_buy0 = self._order_info_insert(agent_id=self.super_user_id, order_type='buy', order_price=self.last_price,
                                             order_lots=Decimal(sell_cnt0), order_round=before_before)
        super_sell1 = self._order_info_insert(agent_id=self.super_user_id, order_type='sell',
                                              order_price=self.last_price, order_lots=Decimal(buy_cnt1),
                                              order_round=before)
        super_buy1 = self._order_info_insert(agent_id=self.super_user_id, order_type='buy', order_price=self.last_price,
                                             order_lots=Decimal(sell_cnt1), order_round=before)
        total_margin = Decimal(0)
        # 插入用户订单并匹配
        for position_info in positions:
            margin_match = Decimal(0)
            if position_info[1] != 0:  # 买
                order_id = self._order_info_insert(agent_id=position_info[0], order_type='buy',
                                                   order_price=self.last_price, order_lots=Decimal(position_info[1]),
                                                   order_round=before_before)
                if order_id != -1:
                    # 订单匹配，并支付保证金
                    margin = (self.margin_rate * Decimal(position_info[1]) * self.last_price).quantize(
                        Decimal('0.0000000'))
                    margin_match += margin
                    match_info = {'bid_order_id': order_id, 'sell_order_id': super_sell0,
                                  'deal_lots': Decimal(position_info[1]), 'deal_price': self.last_price,
                                  'bid_status': 'open', 'bid_security_funds': margin, 'sell_status': 'open',
                                  'sell_security_funds': margin, 'deal_round': before_before, 'deal_num': 0,
                                  'delivery_round': self.contract_round}
                    deal_id = self.db.deal_record_insert(match_info)
                    if deal_id == -1:
                        print(f"将成交单{match_info}插入成交表中失败")
                        exit(-1)
            if position_info[2] != 0:  # 卖
                order_id = self._order_info_insert(agent_id=position_info[0], order_type='sell',
                                                   order_price=self.last_price, order_lots=Decimal(position_info[2]),
                                                   order_round=-1)
                if order_id != -1:
                    # 订单匹配，并支付保证金
                    margin = (self.margin_rate * Decimal(position_info[2]) * self.last_price).quantize(
                        Decimal('0.0000000'))
                    margin_match += margin
                    match_info = {'bid_order_id': super_buy0, 'sell_order_id': order_id,
                                  'deal_lots': Decimal(position_info[2]), 'deal_price': self.last_price,
                                  'bid_status': 'open', 'bid_security_funds': margin, 'sell_status': 'open',
                                  'sell_security_funds': margin, 'deal_round': before_before, 'deal_num': 0,
                                  'delivery_round': self.contract_round}
                    deal_id = self.db.deal_record_insert(match_info)
                    if deal_id == -1:
                        print(f"将成交单{match_info}插入成交表中失败")
                        exit(-1)
            if position_info[3] != 0:  # 买
                order_id = self._order_info_insert(agent_id=position_info[0], order_type='buy',
                                                   order_price=self.last_price, order_lots=Decimal(position_info[3]),
                                                   order_round=before)
                if order_id != -1:
                    # 订单匹配，并支付保证金
                    margin = (self.margin_rate * Decimal(position_info[3]) * self.last_price).quantize(
                        Decimal('0.0000000'))
                    margin_match += margin
                    match_info = {'bid_order_id': order_id, 'sell_order_id': super_sell1,
                                  'deal_lots': Decimal(position_info[3]), 'deal_price': self.last_price,
                                  'bid_status': 'open', 'bid_security_funds': margin, 'sell_status': 'open',
                                  'sell_security_funds': margin, 'deal_round': before, 'deal_num': 0,
                                  'delivery_round': self.contract_round}
                    deal_id = self.db.deal_record_insert(match_info)
                    if deal_id == -1:
                        print(f"将成交单{match_info}插入成交表中失败")
                        exit(-1)
            if position_info[4] != 0:  # 卖
                order_id = self._order_info_insert(agent_id=position_info[0], order_type='sell',
                                                   order_price=self.last_price, order_lots=Decimal(position_info[4]),
                                                   order_round=before)
                if order_id != -1:
                    # 订单匹配，并支付保证金
                    margin = (self.margin_rate * Decimal(position_info[4]) * self.last_price).quantize(
                        Decimal('0.0000000'))
                    margin_match += margin
                    match_info = {'bid_order_id': super_buy1, 'sell_order_id': order_id,
                                  'deal_lots': Decimal(position_info[4]), 'deal_price': self.last_price,
                                  'bid_status': 'open', 'bid_security_funds': margin, 'sell_status': 'open',
                                  'sell_security_funds': margin, 'deal_round': before, 'deal_num': 0,
                                  'delivery_round': self.contract_round}
                    deal_id = self.db.deal_record_insert(match_info)
                    if deal_id == -1:
                        print(f"将成交单{match_info}插入成交表中失败")
                        exit(-1)
            if margin_match == Decimal(0):
                continue
            # 更新用户的账户信息
            results = self.db.agent_record_select(columns='current_funds,security_funds,agent_record_id',
                                                  conditions={'agent_id': position_info[0], 'round': self.round})
            if results == -1:
                print(f"获取玩家{position_info[0]}的当前可用资金失败，进程意外退出")
                exit(-1)
            current_funds = results[0][0] + margin_match
            security_funds = results[0][1] + margin_match
            record_id = results[0][2]
            status = self.db.agent_record_update(
                data={'current_funds': current_funds, 'security_funds': security_funds},
                condition=f'agent_record_id={record_id}')  # 更新存储信息
            if status == -1:
                print(f"在更新玩家{position_info[0]}的账户信息时出错，进程意外退出")
                exit(-1)
            total_margin += margin_match
        # 更新超级用户的账户信息
        results = self.db.agent_record_select(columns='current_funds,security_funds,agent_record_id',
                                              conditions={'agent_id': self.super_user_id, 'round': self.round})
        if results == -1:
            print(f"获取玩家{position_info[0]}的当前可用资金失败，进程意外退出")
            exit(-1)
        current_funds = results[0][0] + total_margin
        security_funds = results[0][1] + total_margin
        record_id = results[0][2]
        status = self.db.agent_record_update(
            data={'current_funds': current_funds, 'security_funds': security_funds},
            condition=f'agent_record_id={record_id}')  # 更新存储信息
        if status == -1:
            print(f"在更新玩家{self.super_user_id}的账户信息时出错，进程意外退出")
            exit(-1)

    def _contract(self, all_agent_record):
        '''
        完成最终交割
        :param all_agent_record:list(tuple),(agent_id，current_funds，available_funds，security_funds，profit_loss)
        '''
        for agent_record in all_agent_record:
            agent_id = agent_record[0]
            available_funds = agent_record[2]
            security_funds = agent_record[3]

            if agent_id == self.super_user_id:  # 跳过超级用户
                continue

            # 获取当前agent的原始资金
            original_capital = self.db.agent_select(columns='init_fund', conditions={'agent_id': agent_id})
            if original_capital == -1:
                print(f"获取{agent_id}玩家的初始资金失败！")
                exit(-1)
            original_capital = original_capital[0][0]

            # 搜索当前agent的待交割交易
            # 获取买单
            buy_orders_sql = f"""
            SELECT `deal_lots`,`deal_price`,`deal_id`
            FROM `deal_record` JOIN `order` ON `order`.`order_id`=`deal_record`.`bid_order_id`
            WHERE `order`.`agent_id`={agent_id} AND `deal_record`.`bid_status`='open'
            """
            buy_orders = self.db.execute_sql(buy_orders_sql)  # 买单,[(成交量，成交价，买方缴纳保证金，成交单编号)]
            if buy_orders is None:
                print(f"计算账户变动信息时，获取{agent_id}的买单信息失败")
                exit(-1)
            total_profit = Decimal(0)  # 总盈亏
            for buy_order in buy_orders:  # 处理每一个买单
                total_profit += (self.last_round_price - buy_order[1]) * buy_order[0]
                status = self.db.deal_record_update(data={'bid_status': 'done'}, condition=f'deal_id={buy_order[2]}')
                if status == -1:
                    print(f"更新成交单{buy_order[2]}的买方状态失败")
                    exit(-1)
            # 获取卖单
            sell_orders_sql = f"""
            SELECT `deal_lots`,`deal_price`,`deal_id`
            FROM `deal_record` JOIN `order` ON `order`.`order_id`=`deal_record`.`sell_order_id`
            WHERE `order`.`agent_id`={agent_id} AND `deal_record`.`sell_status`='open'
            """
            sell_orders = self.db.execute_sql(sell_orders_sql)  # 卖单[(成交量，成交价，缴纳保证金，成交单编号)]
            if sell_orders is None:
                print(f"计算账户变动信息时，获取{agent_id}的卖单信息失败")
                exit(-1)
            for sell_order in sell_orders:  # 处理每一个卖单
                total_profit += (sell_order[1] - self.last_round_price) * sell_order[0]
                status = self.db.deal_record_update(data={'sell_status': 'done'}, condition=f'deal_id={sell_order[2]}')
                if status == -1:
                    print(f"更新成交单{sell_order[2]}的卖方状态失败")
                    exit(-1)

            # 交割结算
            available_funds = available_funds + security_funds + total_profit  # 退还保证金，自负盈亏
            security_funds = Decimal(0)  # 保证金清0
            current_funds = available_funds  # 总资产=可用资金
            real_profit = current_funds - original_capital  # 真正的总盈亏=现有资金-原始资金（因为之前可能发生过平仓）
            agent_record_info = {'agent_id': agent_id, 'round': self.round, 'current_funds': current_funds,
                                 'available_funds': available_funds, 'security_funds': security_funds,
                                 'profit_loss': real_profit}
            status = self.db.agent_record_insert(agent_record_inf=agent_record_info)
            if status == -1:
                print(f"插入玩家{agent_id}在{self.round}轮（最后一轮）的账户信息失败")
                exit(-1)
        return

    def round_end(self):
        """回合结束，当前回合+1，返回增加后的回合数。如果到达最晚交割回合，完成交割"""
        self.round += 1
        # 获取上一轮所有账户信息
        columns = '`agent_id`,`current_funds`,`available_funds`,`security_funds`,`profit_loss`'
        conditions = {'round': self.round - 1}
        all_agent_record = self.db.agent_record_select(columns=columns, conditions=conditions)
        if all_agent_record == -1:  # 失败
            print("获取上一轮所有账户信息失败！进程意外退出")
            exit(-1)

        if self.round > self.contract_round:  # 交割
            self._contract(all_agent_record=all_agent_record)
            print("最终交割完成")
            return self.round

        # 新的一回合，我需要最开始初始化账户信息（将上一轮的账户信息复制过来）
        for agent_record in all_agent_record:
            agent_record_info = {
                'agent_id': agent_record[0],
                'round': self.round,
                'current_funds': agent_record[1],
                'available_funds': agent_record[2],
                'security_funds': agent_record[3],
                'profit_loss': agent_record[4]
            }
            status = self.db.agent_record_insert(agent_record_info)
            if status == -1:  # 失败
                print(f"插入玩家{agent_record[0]}的新一轮信息失败，进程意外退出")
                exit(-1)
        print(f"本回合结束，下一个回合{self.round}，下一回合的账户信息初始化成功")
        return self.round

    def retrieve_market_info(self):
        """
        检索市场信息，返回一个字典，要求包含current_Ni_price, Ni_inventory, Ni_holder, last_turn_trades
        检索基于当前回合 self.round
        :return: 一个字典
        """
        # 获取镍库存，对`actuals`数据库进行操作
        Ni_inventory = self.db.actuals_select(columns='inventory', conditions={'actuals_id': 1})
        if Ni_inventory == -1:
            print("获取镍库存失败，进程意外退出")
            exit(-1)
        Ni_inventory = Ni_inventory[0][0]

        # 获取镍期货价格，它是上一轮的期货平均成交价，对`futures_record`进行操作
        current_Ni_price = self.db.futures_record_select(columns='settlement_price',
                                                         conditions={'futures_id': self.Ni_id, 'round': self.round - 1})
        if Ni_inventory == -1:
            print("获取镍期货价格失败，进程意外退出")
            exit(-1)
        current_Ni_price = float(current_Ni_price[0][0])

        # 镍期货持有信息，排除超级用户的影响
        sql_bid_user = f"""
        SELECT `agent`.`agent_name`,SUM(`deal_record`.`deal_lots`) AS bid_deal
        FROM `order` JOIN `deal_record` ON `deal_record`.`bid_order_id`=`order`.`order_id` JOIN `agent` ON `agent`.`agent_id`=`order`.`agent_id`
        WHERE `deal_record`.`bid_status`='open' AND `agent`.`agent_id`!={self.super_user_id}
        GROUP BY `order`.`agent_id`
        """  # sql语句，买入镍期货合约的用户情况
        bid_user = self.db.execute_sql(sql_bid_user)  # 形式为：[(购买用户名，购买量),...]
        if bid_user is None:
            print("获取买入镍期货合约的用户失败，进程意外退出")
            exit(-1)
        # 将deal_lots转为float
        cnt = 0
        for user in bid_user:
            bid_user[cnt] = (user[0], float(user[1]))
            cnt += 1
        bid_user.sort(key=lambda x: ((-1) * x[1], x[0]))

        sql_sell_user = f"""
        SELECT `agent`.`agent_name`,SUM(`deal_record`.`deal_lots`) AS sell_deal
        FROM `order` JOIN `deal_record` ON `deal_record`.`sell_order_id`=`order`.`order_id` JOIN `agent` ON `agent`.`agent_id`=`order`.`agent_id`
        WHERE `deal_record`.`sell_status`='open' AND `agent`.`agent_id`!={self.super_user_id}
        GROUP BY `order`.`agent_id`
        """  # sql语句，卖出镍期货合约的用户情况
        sell_user = self.db.execute_sql(sql_sell_user)  # 形式为：[(卖出用户名，卖出量),...]
        if sell_user is None:
            print("获取卖出镍期货合约的用户失败，进程意外退出")
            exit(-1)
        cnt = 0
        for user in sell_user:
            sell_user[cnt] = (user[0], float(user[1]))
            cnt += 1
        sell_user.sort(key=lambda x: ((-1) * x[1], x[0]))

        # 上一轮交易情况信息，也排除超级用户的影响
        last_sql_bid_user = f"""
        SELECT `agent`.`agent_name`,SUM(`deal_record`.`deal_lots`) AS bid_deal
        FROM `order` JOIN `deal_record` ON `deal_record`.`bid_order_id`=`order`.`order_id` JOIN `agent` ON `agent`.`agent_id`=`order`.`agent_id`
        WHERE `deal_record`.`deal_round`={self.round - 1} AND `deal_record`.`bid_status`='open' AND `agent`.`agent_id`!={self.super_user_id}
        GROUP BY `order`.`agent_id`
        """  # sql语句，上一轮买入镍期货合约的用户情况
        last_bid_user = self.db.execute_sql(last_sql_bid_user)  # 形式为：[(购买用户名，购买量),...]
        if last_bid_user is None:
            print("获取上一轮买入镍期货合约的用户失败，进程意外退出")
            exit(-1)
        cnt = 0
        for user in last_bid_user:
            last_bid_user[cnt] = (user[0], float(user[1]))
            cnt += 1
        last_bid_user.sort(key=lambda x: ((-1) * x[1], x[0]))

        last_sql_sell_user = f"""
        SELECT `agent`.`agent_name`,SUM(`deal_record`.`deal_lots`) AS sell_deal
        FROM `order` JOIN `deal_record` ON `deal_record`.`sell_order_id`=`order`.`order_id` JOIN `agent` ON `agent`.`agent_id`=`order`.`agent_id`
        WHERE `deal_record`.`deal_round`={self.round - 1} AND `deal_record`.`sell_status`='open' AND `agent`.`agent_id`!={self.super_user_id}
        GROUP BY `order`.`agent_id`
        """  # sql语句，卖出镍期货合约的用户情况
        last_sell_user = self.db.execute_sql(last_sql_sell_user)  # 形式为：[(卖出用户名，卖出量),...]
        if last_sell_user is None:
            print("获取上一轮卖出镍期货合约的用户失败，进程意外退出")
            exit(-1)
        cnt = 0
        for user in last_sell_user:
            last_sell_user[cnt] = (user[0], float(user[1]))
            cnt += 1
        last_sell_user.sort(key=lambda x: ((-1) * x[1], x[0]))

        # print(f"current_Ni_price={current_Ni_price},Ni_inventory={Ni_inventory}\n")

        Ni_holder = {"long(buy)": bid_user, "short(sell)": sell_user}
        last_turn_trades = {"long(buy)": last_bid_user, "short(sell)": last_sell_user}
        # print(f"Ni_holder={Ni_holder}\nlast_turn_trades={last_turn_trades}\n")

        returnDict = {
            "current_Ni_price": current_Ni_price,
            "Ni_inventory": Ni_inventory,
            "Ni_holder": Ni_holder,
            "last_turn_trades": last_turn_trades
        }

        return returnDict

    def retrieve_account_info(self, player_id):
        """
        根据角色id和当前回合，检索当前账户信息
        :param player_id: 角色 id
        :return: Dict
        """

        # 资金信息从`agent_record`中获取
        result = self.db.agent_record_select(columns='current_funds,available_funds,security_funds,profit_loss',
                                             conditions={'agent_id': player_id, 'round': self.round})
        # result的形式为：[(current_funds，available_funds，security_funds)]
        if result == -1:
            print(f"获取玩家{player_id}的账户信息失败，进程意外退出")
            exit(-1)
        capital = float(result[0][0])
        available_deposit = float(result[0][1])
        security_deposit = float(result[0][2])
        profit_loss = float(result[0][3])
        # print(
        # f"<玩家{player_id}>：capital={capital},available_deposit={available_deposit},security_deposit={security_deposit}")

        # 合约信息从deal_record中获取
        Ni_long_sql = f"""
        SELECT SUM(`deal_lots`),`deal_price`
        FROM `deal_record` JOIN `order` ON `deal_record`.`bid_order_id`=`order`.`order_id`
        WHERE `order`.`agent_id`={player_id} AND `deal_record`.`bid_status`='open'
        GROUP BY `deal_price`
        """  # 如果没有信息，则为[]；否则为[(交易量，交易价格),...]
        Ni_long = self.db.execute_sql(Ni_long_sql)
        if Ni_long is None:
            print(f"获取玩家{player_id}的买入合约失败，进程意外退出")
            exit(-1)
        cnt = 0
        for long in Ni_long:
            Ni_long[cnt] = (float(long[0]), float(long[1]))
            cnt += 1
        # print(f"Ni_long={Ni_long}")

        Ni_short_sql = f"""
        SELECT  SUM(`deal_lots`),`deal_price`
        FROM `deal_record` JOIN `order` ON `deal_record`.`sell_order_id`=`order`.`order_id`
        WHERE `order`.`agent_id`={player_id} AND `deal_record`.`sell_status`='open'
        GROUP BY `deal_price`
        """  # 如果没有信息，则为[]；否则为[(交易量，交易价格),...]
        Ni_short = self.db.execute_sql(Ni_short_sql)
        if Ni_short is None:
            print(f"获取玩家{player_id}的卖出合约失败，进程意外退出")
            exit(-1)
        cnt = 0
        for short in Ni_short:
            Ni_short[cnt] = (float(short[0]), float(short[1]))
            cnt += 1
        # print(f"Ni_short={Ni_short}")

        returnDict = {
            "capital": capital,  # - 总资产 float
            "security_deposit": security_deposit,  # - 保证金 float
            "available_deposit": available_deposit,  # - 可用资金 float
            "Ni_long": Ni_long,  # - 多头合约（持有的买单信息） list(tuple)——合并了价格相同的成交订单
            "Ni_short": Ni_short,  # - 空头合约
            "profit_loss": profit_loss  # 盈亏
        }
        return returnDict

    def fund_supplement(self, agent_id: int, amount):
        '''
        补充资金
        :param agent_id:智能体编号
        :param amount：补充资金数（直接增加到可用资金）
        返回：1，更新成功
        '''
        results = self.db.agent_record_select(columns='agent_record_id,current_funds,available_funds',
                                              conditions={'agent_id': agent_id, 'round': self.round})
        if results == -1:
            print(f"在补充资金时，搜索{agent_id}编号玩家的账户信息失败")
            exit(-1)
        agent_record_id = results[0][0]
        current_funds = results[0][1]
        available_funds = results[0][2]
        # 补充资金
        current_funds += Decimal(amount)
        available_funds += Decimal(amount)
        # 更新账户信息
        status = self.db.agent_record_update(data={'current_funds': current_funds, 'available_funds': available_funds},
                                             condition=f'agent_record_id={agent_record_id}')
        if status == -1:
            print(f"在补充资金时，更新{agent_id}编号玩家的账户信息失败")
            exit(-1)
        return 1

    def get_order_info(self):
        '''
        获取本回合截止目前的下单情况
        返回：买单总量，买单平均价格，卖单总量，卖单平均价格
        '''
        buy_order_sql = f"""
        SELECT SUM(`order_lots`),SUM(`order_lots`*`order_price`)/SUM(`order_lots`)
        FROM `order`
        WHERE `order_round`={self.round} AND `order_type`='buy' AND (`order_status`='pending' OR `order_status`='done' OR `order_status`='cancel')
        """
        results = self.db.execute_sql(sql=buy_order_sql)
        if results is None:
            print(f"获取{self.round}轮的下单情况失败")
            exit(-1)
        long_amount = results[0][0]
        long_price = results[0][1]
        if long_amount is None:
            long_amount = 0
            long_price = 0

        sell_order_sql = f"""
        SELECT SUM(`order_lots`),SUM(`order_lots`*`order_price`)/SUM(`order_lots`)
        FROM `order`
        WHERE `order_round`={self.round} AND `order_type`='sell' AND (`order_status`='pending' OR `order_status`='done' OR `order_status`='cancel')
        """
        results = self.db.execute_sql(sql=sell_order_sql)
        if results is None:
            print(f"获取{self.round}轮的下单情况失败")
            exit(-1)
        sell_amount = results[0][0]
        sell_price = results[0][1]
        if sell_amount is None:
            sell_amount = 0
            sell_price = 0

        return float(long_amount), float(long_price), float(sell_amount), float(sell_price)

    def _match_orders_modify(self, buy_orders, sell_orders):
        '''
        撮合交易函数，实现时间优先、价格优先原则，同时避免同一个玩家的订单彼此成交。在订单成交前，会判断可用资金是否充足，若不充足，则不会成交。
        :param buy_orders/sell_orders:list(tuple)，tuple的元组为：(订单编号，玩家编号，剩余未成交量，价格，优先级)
        返回：需要更新remain_lots的买/卖订单，匹配成功的订单
        '''
        cnt_loop=0
        max_iter = len(buy_orders) * len(sell_orders)*2+max(len(buy_orders),len(sell_orders)) #最大允许迭代次数

        # 获取所有玩家编号
        results = self.db.agent_select(columns='agent_id')  # [(agent_id))]
        if results == -1:
            print("获取所有玩家的编号信息失败")
            exit(-1)
        # 获取玩家编号对应的可用资金数
        available_funds = {}  # 记录可用资金数目，available_fund[agent_id]=可用资金
        for i in results:
            agent_id = i[0]
            account = self.db.agent_record_select(columns='available_funds',
                    conditions={'agent_id': agent_id, 'round': self.round})
            if account == -1:
                print(f"获取玩家{agent_id}在{self.round}轮的账户信息失败")
                exit(-1)
            available_funds[agent_id] = account[0][0]
        # 按照买入价格从高到低排序，优先级编号（时间）从低到高排序
        buy_orders.sort(key=lambda x: ((-1) * x[3], x[4]))
        # 按照卖出价格从低到高排序，优先级编号（时间）从低到高排序
        sell_orders.sort(key=lambda x: (x[3], x[4]))

        matches = []  # 记录成交信息,(买家订单编号，卖家订单编号，成交量，成交价格，买方编号，卖方编号，买方出价，卖方出价)[后面四个是为了方便我计算保证金]
        update_buy = {}  # 记录remain_lots有更新的项目，形式为：{订单编号（独一无二的）:(tuple元组)}
        update_sell = {}

        j=0 # 记录当前待匹配的买单下标
        while j < len(buy_orders):  # 买单不为空
            progressed = False  # 防死循环哨兵

            buy_order = buy_orders[j]  # 取出优先级最高的待匹配买单——买单不用担心可用资金不足，因为买单的保证金最多退回/不变，可用资金增加/不变
            buy_volumes = buy_order[2]  # 买方购买量

            if len(sell_orders) > 0:
                if buy_order[3] < sell_orders[0][3]:
                    # 优先级最高的买单价格已经低于卖单价格了，无法匹配，直接退出
                    break
            else:  # 没有sell_orders了
                break

            if cnt_loop>max_iter:
                break

            i=0 # 卖单指针
            while i < len(sell_orders) and buy_volumes>0: # 遍历所有卖单，直至结束/匹配完买单的量
                
                cnt_loop+=1
                if cnt_loop>max_iter:
                    break

                sell_order = sell_orders[i] # 卖单的保证金可能不变/需要补缴，这个时候就需要充足的可用资金了
                # 同一玩家不能成交
                if buy_order[1] == sell_order[1]:
                    i += 1
                    continue

                # 价格不满足，直接结束当前买单
                if buy_order[3] < sell_order[3]:
                    break

                trade_volume = min(buy_volumes, sell_order[2]) # 成交量为买入量和卖出量的最小值

                # === 成交价 ===
                if self.last_price >= buy_order[3]:
                    # 如果上一笔交易成交价大于等于买价，则成交价为买价
                    price = buy_order[3]
                elif self.last_price <= sell_order[3]:
                    # 上一笔交易成交价小于等于卖价，则成交价为卖价
                    price = sell_order[3]
                else:
                    # 处于两者中间，成交价为上一笔成交价
                    price = self.last_price
                
                # 根据可用资金判断是否能够成交
                margin_sell = Decimal(self.margin_rate * (price - sell_order[3]) * trade_volume).quantize(Decimal('0.0000000'))  # 对于卖方来说，需要补缴的保证金
                if margin_sell > available_funds[sell_order[1]]:  # 可用资金不足，当前订单无法成交，判断下一笔卖单
                    i+=1
                    continue

                # === 执行成交 ===
                # 可用资金充足，但这笔订单成交后，买卖双方的可用资金都需要相应变化
                available_funds[sell_order[1]] -= margin_sell
                margin_buy = Decimal(self.margin_rate * (price - buy_order[3]) * trade_volume).quantize(Decimal('0.0000000'))  # 负数，需要退还的保证金
                available_funds[buy_order[1]] -= margin_buy

                matches.append((buy_order[0], sell_order[0], trade_volume, price, buy_order[1], sell_order[1],buy_order[3], sell_order[3]))  # 成交信息
                self.last_price = price  # 更新上一笔交易的价格
                progressed = True  # 有进展

                # 更新买单买入量，要全部赋值，因为tuple不支持单item更新
                buy_order = (buy_order[0], buy_order[1], buy_order[2] - trade_volume, buy_order[3], buy_order[4])
                buy_volumes -= trade_volume
                update_buy[buy_order[0]] = buy_order

                sell_remain = sell_order[2] - trade_volume
                sell_order = (sell_order[0], sell_order[1], sell_remain, sell_order[3], sell_order[4])
                sell_orders[i] = sell_order
                update_sell[sell_order[0]] = sell_order

                if sell_remain == 0: # 卖单已经全部卖出，更新卖单队列
                    sell_orders.pop(i) # 不应该修改i的值，因为匹配完的已经删除了，下一个待匹配的下标仍旧为1
                else:  # 未全部卖出，更新卖单队列内容（且此时必定意味着买方已经全部成交）
                    sell_orders[i] = sell_order
                    i+=1

                if buy_volumes==0: #买单已全部匹配，处理下一个
                    buy_orders.pop(j)
                    j=0
                    break
            
            # 如果这一轮啥也没发生，强制推进 j
            if not progressed:
                j+=1

        return update_buy, update_sell, matches

    def _pay_margin(self, player_id, margin):
        '''
        缴纳保证金
        :param player_id：玩家编号
        :param margin:要缴纳的保证金价格，正数说明是缴纳，负数说明是退还
        '''
        margin = Decimal(margin).quantize(Decimal('0.0000000'))
        # 先获取当前可用资金，查看是否足以缴纳保证金
        results = self.db.agent_record_select(columns='available_funds,security_funds,agent_record_id',
                                              conditions={'agent_id': player_id, 'round': self.round})
        if results == -1:
            print(f"获取玩家{player_id}的当前可用资金失败，进程意外退出")
            exit(-1)
        available_funds = results[0][0]
        security_funds = results[0][1]
        record_id = results[0][2]
        if available_funds < margin:  # 不足以缴纳保证金
            return 0
        available_funds -= margin  # 更新可用资金
        security_funds += margin  # 更新保证金
        if security_funds < 0:
            if security_funds < -1:
                print(
                    f"<Error>:{self.round}轮出现未知情况，{player_id}的保证金居然小于-1！margin={margin},security={security_funds},available={available_funds}")
                error_file.write(
                    f"<Error>:{self.round}轮出现未知情况，{player_id}的保证金居然小于-1！margin={margin},security={security_funds},available={available_funds}，但为了安全考虑，保证金设置为0\n")
            else:
                print(
                    f"<Warning>:{self.round}轮出现未知情况，{player_id}的保证金居然在-1到0之间！margin={margin},security={security_funds},available={available_funds}")
                error_file.write(
                    f"<Error>:{self.round}轮出现未知情况，{player_id}的保证金居然小于-1！margin={margin},security={security_funds},available={available_funds}，但为了安全考虑，保证金设置为0\n")
            security_funds = 0
        status = self.db.agent_record_update(
            data={'available_funds': available_funds, 'security_funds': security_funds},
            condition=f'agent_record_id={record_id}')  # 更新存储信息
        if status == -1:
            print(f"在更新玩家{player_id}的账户信息时出错，进程意外退出")
            exit(-1)
        return 1

    def deal_making(self, transactions: list):
        """
        transactions 中包含用户 ID 信息
        其它对交易撮合有需要的信息，在此处标注
        “key” - 解释
        :param transactions: list
        形式为list(list)，每个小list的内容为[用户ID，下单回合，订单类型（请将买入卖出换成buy和sell)，买入/卖出量（请给数据），单位价格（请给数据）]
        :return:
            【不返回】改变实参：transactions：从 [agent_id, turn, type, amount, price]到 [agent_id, order_id, turn, type, amount, price]【增加了订单对应编号】
            succeeded_requests - 成功达成交易的请求, list[tuple], tuple[0] 为用户 ID (用户编号，订单编号，类型，成交量，成交价格)
            failed_requests - 未能达成交易的请求, list[tuple], tuple[0] 为用户 ID （用户编号，订单编号，类型，未成交量，设定价格，未成交原因）【因为只能取消当前轮次的单，所以我只给出在当前轮次打出的订单未成交的情况，不是所有未成功的交易！！】——未成交原因：pending，只是单纯匹配失败；no_margin：可用资金不足以缴纳初始保证金（也就是保证金率*交易量*给出价格）；invalid：价格超出涨停限制。
            deals - 存入数据库中的交易, list[tuple]
        """
        if len(transactions) == 0:  # 没有交易
            return [], [], []
        turn = transactions[0][1]
        # 首先，将订单插入order中并扣除保证金，并在这个时候检查价格是否超过涨跌限制，若超过，直接将状态设置为'无效'(invalid)
        high_price = self.last_round_price * (1 + self.price_limit)  # 最高价
        low_price = self.last_round_price * (1 - self.price_limit)  # 最低价
        cnt = 0  # 已经处理的order数量
        for transaction in transactions:
            order_inf = {
                'agent_id': transaction[0],
                'futures_id': self.Ni_id,
                'order_type': transaction[2],
                'order_price': transaction[4],
                'order_lots': transaction[3],
                'remain_lots': transaction[3],
                'order_round': self.round,
                'order_num': transaction[1]
            }
            if Decimal(transaction[4]) >= low_price and Decimal(transaction[4]) <= high_price:  # 正常价格
                order_inf['order_status'] = 'pending'
                status = self.db.order_insert(order_inf)
                if status == -1:
                    print(f"玩家{transaction[0]}的本轮交易插入失败，进程意外退出")
                    exit(-1)
                transactions[cnt].insert(1,
                                         status)  # 从[agent_id, turn, type, amount, price]变成[agent_id, order_id, turn, type, amount, price]
                # transactions变了之后，transaction也变了
                cnt += 1
            else:  # 超过波动，直接无法参加下一波交易
                order_inf['order_status'] = 'invalid'
                status = self.db.order_insert(order_inf)
                if status == -1:
                    print(f"玩家{transaction[0]}的本轮交易插入失败，进程意外退出")
                    exit(-1)
                transactions[cnt].insert(1,
                                         status)  # 从[agent_id, turn, type, amount, price]变成[agent_id, order_id, turn, type, amount, price]
                cnt += 1
                continue

            # 下单时先自动扣除保证金，为出价*保证金率（如果订单成交了，需要再将其与合同成交价对比返回对应保证金？）
            margin = (self.margin_rate * Decimal(transaction[4]) * Decimal(transaction[5])).quantize(
                Decimal('0.0000000'))  # 保证金=保证金率*期货合约量*单位价格
            res = self._pay_margin(transaction[0], margin)
            if res == 0:
                # 说明可用资金不足以缴纳保证金，状态自动变为no_margin(无充足可用资金)
                res = self.db.order_update(data={'order_status': 'no_margin'}, condition=f'order_id={status}')
                if res == -1:
                    print(f"玩家{transaction[0]}所下订单无充足可用资金，order_id={status}，但状态更新失败")
                    exit(-1)
        # print(f"将订单编号插入后，transactions={transactions}")
        # input("初始保证金扣除成功")

        # 进行交易撮合
        # 首先找出本轮中未成功交易的订单（编号是唯一标识）
        buy_deals = self.db.order_select(columns='order_id,agent_id,remain_lots,order_price,order_num',
                                         conditions={'order_type': 'buy', 'order_round': self.round,
                                                     'order_status': 'pending'})
        if buy_deals == -1:
            print(f"找出{self.round}轮中（第{turn}回合）的待撮合买单交易失败！")
            exit(-1)

        sell_deals = self.db.order_select(columns='order_id,agent_id,remain_lots,order_price,order_num',
                                          conditions={'order_type': 'sell', 'order_round': self.round,
                                                      'order_status': 'pending'})
        if sell_deals == -1:
            print(f"找出{self.round}轮中（第{turn}回合）的待撮合卖单交易失败！")
            exit(-1)

        # 交易撮合部分,matches=(买家订单编号，卖家订单编号，成交量，成交价格，买方编号，卖方编号，买方出价，卖方出价）
        # update_buy, update_sell, matches = self._mathch_orders_new(buy_orders=buy_deals, sell_orders=sell_deals)
        update_buy, update_sell, matches = self._match_orders_modify(buy_orders=buy_deals, sell_orders=sell_deals)  
        # print(f"update_buy={update_buy}\nupdate_sell={update_sell}\nmatches={matches}")

        # 更新买单的剩余量
        for key, i in update_buy.items():
            if i[2] == 0:  # 全部卖光，还需要更新状态
                status = self.db.order_update(data={'remain_lots': i[2], 'order_status': 'done'},
                                              condition=f'order_id={i[0]}')
                if status == -1:
                    print(f"下单买单编号{i[0]}已经全部买入，状态更新失败")
                    exit(-1)
            else:
                status = self.db.order_update(data={'remain_lots': i[2]}, condition=f'order_id={i[0]}')
                if status == -1:
                    print(f"下单买单编号{i[0]}已买入部分，状态更新失败")
                    exit(-1)
        # 更新卖单的剩余量
        for key, i in update_sell.items():
            if i[2] == 0:
                status = self.db.order_update(data={'remain_lots': i[2], 'order_status': 'done'},
                                              condition=f'order_id={i[0]}')
                if status == -1:
                    print(f"下单买单编号{i[0]}已经全部卖出，状态更新失败")
                    exit(-1)
            else:
                status = self.db.order_update(data={'remain_lots': i[2]}, condition=f'order_id={i[0]}')
                if status == -1:
                    print(f"下单买单编号{i[0]}已卖出部分，状态更新失败")
                    exit(-1)
        # no_available_agent_record_id=list()
        # 将成交单加入成交表中，并且更新缴纳的保证金
        for i in matches:
            margin_match = (self.margin_rate * i[3] * i[2]).quantize(Decimal('0.0000000'))  # 双方实际缴纳的保证金数值
            match_info = {'bid_order_id': i[0], 'sell_order_id': i[1], 'deal_lots': i[2], 'deal_price': i[3],
                          'bid_status': 'open', 'bid_security_funds': margin_match, 'sell_status': 'open',
                          'sell_security_funds': margin_match, 'deal_round': self.round, 'deal_num': turn,
                          'delivery_round': self.contract_round}
            deal_id = self.db.deal_record_insert(match_info)
            if deal_id == -1:
                print(f"将成交单{match_info}插入成交表中失败")
                exit(-1)

            # 保证金缴纳更新，双方需要再缴纳的保证金为(成交价-出价)*保证金率*成交量
            margin_buy = ((i[3] - i[6]) * self.margin_rate * i[2]).quantize(Decimal('0.0000000'))
            margin_sell = ((i[3] - i[7]) * self.margin_rate * i[2]).quantize(Decimal('0.0000000'))
            status = self._pay_margin(i[4], margin_buy)
            if status == 0:  # 在撮合函数下，不可能出现这种情况，除非撮合函数出错【本质上说，这种情况肯定不会发生，因为买方最多退还保证金/保证金不变
                print(f"在处理{deal_id}成交单时，买方玩家{i[4]}的账户可用资金居然不足以缴纳保证金，这说明撮合函数错误")
                error_file.write(
                    f"<Error>{self.round}轮中，在处理{deal_id}成交单时，买方玩家{i[4]}的账户可用资金居然不足以缴纳保证金，这说明撮合函数错误。撮合结果信息为：update_buy={update_buy},update_sell={update_sell},matches={matches}。无对应处理办法，且未扣除该项保证金，相当于它的账户上额外增加了{margin_buy}元\n")
            status = self._pay_margin(i[5], margin_sell)
            if status == 0:
                print(f"在处理{deal_id}成交单时，卖方玩家{i[5]}的账户可用资金居然不足以缴纳保证金，这说明撮合函数错误")
                error_file.write(
                    f"<Error>{self.round}轮中，在处理{deal_id}成交单时，卖方玩家{i[5]}的账户可用资金居然不足以缴纳保证金，这说明撮合函数错误。撮合结果信息为：update_buy={update_buy},update_sell={update_sell},matches={matches}。无对应处理办法，且未扣除该项保证金，相当于它的账户上额外增加了{margin_sell}元\n")
        succeeded_requests_sql = f"""
        SELECT `order`.`agent_id`,`order`.`order_id`,`order`.`order_type`,`deal_record`.`deal_lots`,`deal_record`.`deal_price`
        FROM `deal_record` JOIN `order` ON `order`.`order_id`=`deal_record`.`bid_order_id` OR `order`.`order_id`=`deal_record`.`sell_order_id`
        WHERE `deal_record`.`deal_round`={self.round} AND `deal_record`.`deal_num`={turn}
        """
        succeeded_requests = self.db.execute_sql(
            succeeded_requests_sql)  # 成功达成交易的请求，list(tuple)，(用户编号，订单编号，类型，成交量，成交价格)
        if succeeded_requests is None:
            print(f"获取在{self.round}的{turn}回合中撮合成功的交易请求失败")
            exit(-1)
        cnt = 0
        for requests in succeeded_requests:
            succeeded_requests[cnt] = (requests[0], requests[1], requests[2], float(requests[3]), float(requests[4]))
            cnt += 1

        failed_requests_sql = f"""
        SELECT `agent_id`,`order_id`,`order_type`,`remain_lots`,`order_price`,`order_status`
        FROM `order`
        WHERE `order_round`={self.round} AND `order_num`={turn} AND `order_status`='pending'
        """
        failed_requests = self.db.execute_sql(
            failed_requests_sql)  # （用户编号，订单编号，类型，未成交量，设定价格，未成交原因）【因为只能取消当前轮次的单，所以我只给出在当前轮次打出的订单未成交的情况，不是所有未成功的交易！！】
        if failed_requests is None:
            print(f"获取在{self.round}的{turn}回合中撮合失败的交易请求失败")
            exit(-1)
        cnt = 0
        for requests in failed_requests:
            failed_requests[cnt] = (
            requests[0], requests[1], requests[2], float(requests[3]), float(requests[4]), requests[5])
            cnt += 1

        deals_sql = f"""
        SELECT *
        FROM `deal_record`
        WHERE `deal_round`={self.round} AND `deal_num`={turn}
        """
        deals = self.db.execute_sql(deals_sql)  # 我不知道想要的到底是什么，所以我只给出了成交订单的信息，
        if deals is None:
            print(f"获取在{self.round}的{turn}回合中成交的订单信息失败")
            exit(-1)

        # print(f"succeeded_requests={succeeded_requests}\nfailed_requests={failed_requests}\ndeals={deals}\n")

        return succeeded_requests, failed_requests, deals

    def withdraw_requests(self, withdraw_requests: list):
        """
        处理撤单请求，新增撤单记录，刷新账户可用资金
        :param withdraw_requests: 撤单请求列表 list[order_id]
        :return: 0
        """
        # 撤单，需要更新order并退还保证金
        for i in withdraw_requests:
            # 先找出对应订单
            results = self.db.order_select(columns='order_price,remain_lots,order_status,agent_id',
                                           conditions={'order_id': i})
            if results == -1:
                print("获取要撤销的订单信息失败！")
                exit(-1)
            order_price = results[0][0]
            remain_lots = results[0][1]
            order_status = results[0][2]
            agent_id = results[0][3]
            if order_status != 'pending':
                print(f"订单编号{i}对应订单并不是等待撮合状态，而是{order_status}，无法取消")
                continue
            # 全部取消，订单状态变成cancel即可
            status = self.db.order_update(data={'order_status': 'cancel'}, condition=f'order_id={i}')
            if status == -1:
                print(f"更新订单{i}失败")
                exit(-1)
            margin = (-1 * remain_lots * order_price * self.margin_rate).quantize(Decimal('0.0000000'))  # 退还保证金
            self._pay_margin(agent_id, margin)  # 更新数据库中的可用资金和保证金
        return 0

    def _close_position_for_buy(self, deal_id: int, abs_profit: Decimal, buy_account_id: int):
        '''
        强制平仓（针对买方），只针对某一个玩家的某一笔订单，买方平仓，那卖方自然也会平仓（赚钱)
        :param deal_id:成交订单编号
        :param abs_profit:盈亏的绝对值
        :param buy_account_id：买方的账户信息编号
        ------
        return：买方强制平仓后的可用资金和保证金（方便在平仓此笔订单后，处理后续订单）
        '''
        # input(f"对订单{deal_id}进行强制平仓（由于买方），盈亏为{abs_profit}")
        result = self.db.deal_record_select(columns='sell_order_id,bid_security_funds,sell_security_funds',
                                            conditions={'deal_id': deal_id})
        if result == -1:
            print(f"获取成交订单{deal_id}信息失败")
            exit(-1)
        sell_order_id = result[0][0]
        bid_security_funds = result[0][1]
        sell_security_funds = result[0][2]
        # available_funds_status=-1 #说明可用资金不为负数

        # 对于买方，强制平仓，退还保证金为可用资金，可用资金减去亏损资金
        result = self.db.agent_record_select(columns='current_funds,available_funds,security_funds',
                                             conditions={'agent_record_id': buy_account_id})
        if result == -1:
            print(f"获取买方玩家的账户信息（编号{buy_account_id})失败")
            exit(-1)
        buy_current_funds = result[0][0]
        buy_available_funds = result[0][1]
        buy_security_funds = result[0][2]
        buy_security_funds -= bid_security_funds  # 本笔订单的保证金归0
        buy_available_funds = buy_available_funds + bid_security_funds - abs_profit  # 退还本笔保证金为可用资金，但同时需要承担亏损（亏损金额绝对值为abs_profit）
        # if buy_available_funds<0: #无法覆盖这个亏损，可用资金状态不对
        #     available_funds_status=1
        buy_current_funds -= abs_profit  # 亏损也会体现在总资金上
        status = self.db.agent_record_update(
            data={'current_funds': buy_current_funds, 'available_funds': buy_available_funds,
                  'security_funds': buy_security_funds}, condition=f'agent_record_id={buy_account_id}')  # 更新账户信息
        if status == -1:
            print(f"更新买方玩家的账户信息（编号{buy_account_id})失败")
            exit(-1)

        # 对于卖方，因买方平仓，该笔订单结束，退还保证金为可用资金，同时获得盈利
        # 根据卖方订单编号获取卖方编号
        result = self.db.order_select(columns='agent_id', conditions={'order_id': sell_order_id})
        if result == -1:
            print(f"根据下单编号{sell_order_id}获取卖方编号agent_id失败")
            exit(-1)
        sell_player_id = result[0][0]
        # 获取卖方账户信息
        result = self.db.agent_record_select(columns='agent_record_id,current_funds,available_funds,security_funds',
                                             conditions={'agent_id': sell_player_id, 'round': self.round})
        if result == -1:
            print(f"根据卖方编号{sell_player_id}获取卖方在{self.round}轮的账户信息失败")
            exit(-1)
        short_account_id = result[0][0]
        short_current_funds = result[0][1]
        short_available_funds = result[0][2]
        short_security_funds = result[0][3]
        short_security_funds -= sell_security_funds  # 本笔订单保证金归还
        short_available_funds = short_available_funds + sell_security_funds + abs_profit  # 归还保证金，获取利润
        short_current_funds += abs_profit  # 盈利也体现在总资产上
        status = self.db.agent_record_update(
            data={'current_funds': short_current_funds, 'available_funds': short_available_funds,
                  'security_funds': short_security_funds}, condition=f'agent_record_id={short_account_id}')  # 更新账户信息
        if status == -1:
            print(f"更新卖方玩家的账户信息（编号{short_account_id})失败")
            exit(-1)

        # 更新成交单的买卖双方状态和结算轮次
        status = self.db.deal_record_update(
            data={'bid_status': 'close', 'sell_status': 'done', 'delivery_round': self.round},
            condition=f'deal_id={deal_id}')
        if status == -1:
            print(f"更新成交单{deal_id}的买卖双方状态和结算轮次失败")
            exit(-1)

        # input(f"对订单{deal_id}进行强制平仓（由于买方），盈亏为{abs_profit},平仓结束")
        return buy_available_funds, buy_security_funds
        # return buy_available_funds,buy_security_funds,available_funds_status

    def _close_position_for_sell(self, deal_id: int, abs_profit: Decimal, sell_account_id: int):
        '''
        强制平仓（针对卖方），只针对某一个玩家的某一笔订单，卖方平仓，那买方自然也会平仓（赚钱)
        :param deal_id:成交订单编号
        :param abs_profit:盈亏的绝对值
        :param sell_account_id：买方的账户信息编号
        ------
        return：卖方强制平仓后的可用资金和保证金（方便在平仓此笔订单后，处理后续订单）
        '''
        # input(f"对订单{deal_id}进行强制平仓（由于卖方），盈亏为{abs_profit}")
        result = self.db.deal_record_select(columns='bid_order_id,bid_security_funds,sell_security_funds',
                                            conditions={'deal_id': deal_id})
        if result == -1:
            print(f"获取成交订单{deal_id}信息失败")
            exit(-1)
        bid_order_id = result[0][0]
        bid_security_funds = result[0][1]
        sell_security_funds = result[0][2]
        # available_funds_status=-1 #可用资金状态，-1说明不为负

        # 对于卖方，强制平仓，退还保证金为可用资金，可用资金减去亏损资金
        result = self.db.agent_record_select(columns='current_funds,available_funds,security_funds',
                                             conditions={'agent_record_id': sell_account_id})
        if result == -1:
            print(f"获取买方玩家的账户信息（编号{sell_account_id})失败")
            exit(-1)
        short_current_funds = result[0][0]
        short_available_funds = result[0][1]
        short_security_funds = result[0][2]
        short_security_funds -= sell_security_funds  # 本笔订单的保证金归0
        short_available_funds = short_available_funds + sell_security_funds - abs_profit  # 退还本笔保证金为可用资金，但同时需要承担亏损（亏损金额绝对值为abs_profit）
        # if short_available_funds<0: #无法覆盖这个亏损，可用资金状态不对
        #     available_funds_status=-1
        short_current_funds -= abs_profit  # 亏损也会体现在总资金上
        status = self.db.agent_record_update(
            data={'current_funds': short_current_funds, 'available_funds': short_available_funds,
                  'security_funds': short_security_funds}, condition=f'agent_record_id={sell_account_id}')  # 更新账户信息
        if status == -1:
            print(f"更新卖方玩家的账户信息（编号{sell_account_id})失败")
            exit(-1)

        # 对于买方，因卖方平仓，该笔订单结束，退还保证金为可用资金，同时获得盈利
        # 根据买方订单编号获取买方编号
        result = self.db.order_select(columns='agent_id', conditions={'order_id': bid_order_id})
        if result == -1:
            print(f"根据下单编号{bid_order_id}获取买方编号agent_id失败")
            exit(-1)
        buy_player_id = result[0][0]
        # 获取买方账户信息
        result = self.db.agent_record_select(columns='agent_record_id,current_funds,available_funds,security_funds',
                                             conditions={'agent_id': buy_player_id, 'round': self.round})
        if result == -1:
            print(f"根据买方编号{buy_player_id}获取买方在{self.round}轮的账户信息失败")
            exit(-1)
        buy_account_id = result[0][0]
        buy_current_funds = result[0][1]
        buy_available_funds = result[0][2]
        buy_security_funds = result[0][3]
        buy_security_funds -= bid_security_funds  # 本笔订单保证金归还
        buy_available_funds = buy_available_funds + bid_security_funds + abs_profit  # 归还保证金，获取利润
        buy_current_funds += abs_profit  # 盈利也体现在总资产上
        status = self.db.agent_record_update(
            data={'current_funds': buy_current_funds, 'available_funds': buy_available_funds,
                  'security_funds': buy_security_funds}, condition=f'agent_record_id={buy_account_id}')  # 更新账户信息
        if status == -1:
            print(f"更新买方玩家的账户信息（编号{buy_account_id})失败")
            exit(-1)

        # 更新成交单的买卖双方状态和结算轮次
        status = self.db.deal_record_update(
            data={'bid_status': 'done', 'sell_status': 'close', 'delivery_round': self.round},
            condition=f'deal_id={deal_id}')
        if status == -1:
            print(f"更新成交单{deal_id}的买卖双方状态和结算轮次失败")
            exit(-1)

        # input(f"对订单{deal_id}进行强制平仓（由于卖方），盈亏为{abs_profit},平仓结束")
        return short_available_funds, short_security_funds
        # return short_available_funds,short_security_funds,available_funds_status

    def _cal_avg_price(self):
        '''
        计算本回合的平均成交价格
        最后一轮有成交单，为最后一轮平均成交价——本回合有成交单，为本回合成交价——上一回合的价格
        返回：平均价格
        '''
        # 首先计算平均价格，futures_record表中插入本轮交易的信息
        # 在最后一轮有成交单的情况下，平均价格=最后一轮的平均成交价格
        avg_price = self.db.deal_record_select(columns='SUM(`deal_lots`*`deal_price`)/SUM(`deal_lots`)',
                                               conditions={'deal_round': self.round, 'deal_num': 4})
        if avg_price == -1:
            print(f"获取{self.round}轮最后一轮的平均价格失败")
            exit(-1)
        avg_price = avg_price[0][0]
        if avg_price is None:  # 最后一轮没有成交单，取本回合的平均成交价格
            # 平均价格=(成交量*成交价格)之和/总成交量
            avg_price = self.db.deal_record_select(columns='SUM(`deal_lots`*`deal_price`)/SUM(`deal_lots`)',
                                                   conditions={'deal_round': self.round})
            if avg_price == -1:
                print(f"获取{self.round}回合5轮的平均价格失败")
                exit(-1)
            avg_price = avg_price[0][0]
        if avg_price is None:  # 因为一笔订单也没有成交，所以平均价格与上一轮的价格相同
            print("在本轮中，没有成交订单")
            avg_price = self.last_round_price
        else:
            # 在新的一轮交易中，上一笔订单的交易价设为上一轮的最终平均价格，更新记录上一轮成交价的变量
            self.last_price = Decimal(avg_price)
            self.last_round_price = Decimal(avg_price)
        futures_record_info = {'futures_id': self.Ni_id, 'round': self.round, 'settlement_price': avg_price}
        status = self.db.futures_record_insert(futures_record_info)
        if status == -1:
            print(f"插入期货在{self.round}轮的交易价格信息失败")
            exit(-1)
        print(f"本回合的平均成交价={avg_price},status={status}")
        return avg_price

    def settlement_of_round(self):
        """
        账户重新结算，计算最新价格，刷新账户资产，计算平仓问题
        :return: 0
        """
        avg_price = self._cal_avg_price()  # 计算平均成交价格

        # 对于目前order中未成交的订单，都应该关闭并返回保证金
        close_order = self.db.order_select(columns='order_id,agent_id,order_price,remain_lots',
                                           conditions={'order_status': 'pending',
                                                       'order_round': self.round})  # [(订单编号，智能体编号，订单价格，剩余未成交量)]
        if close_order == -1:
            print(f"获取{self.round}轮中未成交的订单信息失败")
            exit(-1)
        for i in close_order:
            # 更新订单状态(关闭)
            status = self.db.order_update(data={'order_status': 'close'}, condition=f'order_id={i[0]}')
            if status == -1:
                print(f"更新{self.round}轮中未成交的订单{i[0]}的状态失败")
                exit(-1)
            # 退还保证金，更新账户余额
            margin = (-i[2] * i[3] * self.margin_rate).quantize(Decimal('0.0000000'))
            self._pay_margin(i[1], margin)
        # print("订单关闭，退还保证金成功")

        # 计算账户的变动信息，根据平均成交价格计算盈亏金额、是否需要新增保证金、当前资金和可用资金等的变化
        # 盈亏金额：对于买单，等于现价-合约价；对于卖单，等于合约价-现价。现价在这里是当日平均期货成交价
        # 如果保证金不足以覆盖亏损的钱，那么需要补充保证金至亏损资金
        # 获取所有玩家的编号
        all_player = self.db.agent_select(columns='agent_id')
        profits_info = {}  # agent_record_id:profit_loss
        # 根据玩家编号获取他们的账户信息、买单和卖单
        for i in all_player:
            player_id = i[0]
            if player_id == self.super_user_id:  # 不需要处理超级用户
                continue
            # 获取账户信息
            account = self.db.agent_record_select(columns='agent_record_id,available_funds,security_funds',
                                                  conditions={'agent_id': player_id, 'round': self.round})
            if account == -1:
                print(f"计算账户变动信息时，获取{player_id}的账户信息失败")
                exit(-1)
            flag = False  # 如果flag为True，说明该玩家的账户可用资金可能为负
            agent_record_id = account[0][0]
            available_funds = account[0][1]
            security_funds = account[0][2]

            # 获取买单
            buy_orders_sql = f"""
            SELECT `deal_lots`,`deal_price`,`bid_security_funds`,`deal_id`
            FROM `deal_record` JOIN `order` ON `order`.`order_id`=`deal_record`.`bid_order_id`
            WHERE `order`.`agent_id`={player_id} AND `deal_record`.`bid_status`='open'
            """
            buy_orders = self.db.execute_sql(buy_orders_sql)  # 买单,[(成交量，成交价，买方缴纳保证金，成交单编号)]
            if buy_orders is None:
                print(f"计算账户变动信息时，获取{player_id}的买单信息失败")
                exit(-1)
            total_profit = Decimal(0)  # 总盈亏
            for buy_order in buy_orders:  # 处理每一个买单
                profit = (avg_price - buy_order[1]) * buy_order[0]
                if profit < 0:  # 说明亏损，我们需要要求保证金大于|亏损|
                    if buy_order[2] < -profit:  # 说明不足以覆盖亏损，应该补充缴纳保证金至-profit
                        margin = ((-profit) - buy_order[2]).quantize(Decimal('0.0000000'))  # 补充缴纳的金额
                        if available_funds < margin:  # 无充足可用资金，强制平仓
                            available_funds, security_funds = self._close_position_for_buy(deal_id=buy_order[3],
                                                                                           abs_profit=-profit,
                                                                                           buy_account_id=agent_record_id)
                            # if available_funds_status==1:
                            #     flag=True
                        else:  # 补充缴纳保证金
                            available_funds -= margin
                            security_funds += margin
                            status = self.db.agent_record_update(
                                data={'available_funds': available_funds, 'security_funds': security_funds},
                                condition=f'agent_record_id={agent_record_id}')  # 更新账户信息
                            if status == -1:
                                print(f"玩家{player_id}的账户信息（编号{agent_record_id}）更新失败")
                                exit(-1)
                            status = self.db.deal_record_update(data={'bid_security_funds': (-profit)},
                                                                condition=f'deal_id={buy_order[3]}')
                            if status == -1:
                                print(f"玩家{player_id}的成交单信息（编号{buy_order[3]}，买方）更新失败")
                                exit(-1)
                            total_profit += profit  # 计入总盈亏
                    else:  # 足以覆盖亏损，计入总盈亏
                        total_profit += profit
                else:  # 赚钱，计入总盈亏即可
                    total_profit += profit
            # 获取卖单
            sell_orders_sql = f"""
            SELECT `deal_lots`,`deal_price`,`sell_security_funds`,`deal_id`
            FROM `deal_record` JOIN `order` ON `order`.`order_id`=`deal_record`.`sell_order_id`
            WHERE `order`.`agent_id`={player_id} AND `deal_record`.`sell_status`='open'
            """
            sell_orders = self.db.execute_sql(sell_orders_sql)  # 卖单[(成交量，成交价，缴纳保证金，成交单编号)]
            if sell_orders is None:
                print(f"计算账户变动信息时，获取{player_id}的卖单信息失败")
                exit(-1)
            for sell_order in sell_orders:  # 处理每一个卖单
                profit = (sell_order[1] - avg_price) * sell_order[0]
                if profit < 0:  # 说明亏损，我们需要要求保证金大于|亏损|
                    if sell_order[2] < -profit:  # 说明不足以覆盖亏损，应该补充缴纳保证金至-profit
                        margin = ((-profit) - sell_order[2]).quantize(Decimal('0.0000000'))  # 补充缴纳的金额
                        if available_funds < margin:  # 无充足可用资金，强制平仓
                            available_funds, security_funds = self._close_position_for_sell(deal_id=sell_order[3],
                                                                                            abs_profit=-profit,
                                                                                            sell_account_id=agent_record_id)
                            # if available_funds_status==1:
                            #     flag=True
                        else:  # 补充缴纳保证金
                            available_funds -= margin
                            security_funds += margin
                            status = self.db.agent_record_update(
                                data={'available_funds': available_funds, 'security_funds': security_funds},
                                condition=f'agent_record_id={agent_record_id}')  # 更新账户信息
                            if status == -1:
                                print(f"玩家{player_id}的账户信息（编号{agent_record_id}）更新失败")
                                exit(-1)
                            status = self.db.deal_record_update(data={'sell_security_funds': (-profit)},
                                                                condition=f'deal_id={sell_order[3]}')
                            if status == -1:
                                print(f"玩家{player_id}的成交单信息（编号{sell_order[3]}，卖方）更新失败")
                                exit(-1)
                            total_profit += profit  # 计入总盈亏
                    else:  # 可以覆盖亏损，计入总盈亏
                        total_profit += profit
                else:  # 赚钱，计入总盈亏即可
                    total_profit += profit

            profits_info[agent_record_id] = total_profit  # 记录盈亏信息
        # print(f"---profits_info={profits_info}")
        # 最终结算
        for account_id, profits in profits_info.items():
            # print(f"account_id={account_id},profits={profits}")
            results = self.db.agent_record_select(columns='available_funds,security_funds',
                                                  conditions={'agent_record_id': account_id})
            if results == -1:
                print(f"获取账户记录{agent_record_id}失败")
                exit(-1)
            available_funds = results[0][0]
            if available_funds < 0:  # 在所有平仓结束后，可用资金为负，设置为0
                available_funds = Decimal(0)
            security_funds = results[0][1]
            current_funds = available_funds + security_funds + profits  # 目前的总资产
            # print(f"available_funds={available_funds},security_funds={security_funds},current_funds={current_funds}")
            status = self.db.agent_record_update(
                data={'current_funds': current_funds, 'available_funds': available_funds,
                      'security_funds': security_funds, 'profit_loss': profits},
                condition=f'agent_record_id={account_id}')
            if status == -1:
                print(f"更新{player_id}的账户变动信息失败")
                exit(-1)
            # print(f"status={status}")
        # print("账户变动信息更新成功！")

        return float(avg_price)
