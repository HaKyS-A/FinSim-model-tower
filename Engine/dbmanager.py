# pip install mysql-connector-python
# pip install DBUtils
import mysql.connector
from dbutils.pooled_db import PooledDB
from mysql.connector import Error


class DatabaseManager:
    """ 数据库基本功能类 """

    # 初始化数据库连接
    def __init__(self, host, port, user, password):

        self.pool = PooledDB(
            creator=mysql.connector,  # 连接模块
            mincached=10,  # 连接池
            maxconnections=200,  # 连接池允许的最大连接数，0和None表示不限制连接数
            blocking=True,  # 连接池中如果没有可用连接后，是否阻塞等待。True，等待；False，不等待然后报错
            host=host,
            port=port,
            user=user,
            password=password,
            # database = db_name
        )

        # 打开数据库连接
        try:
            self._conn = self.pool.connection()
            self._cursor = self._conn.cursor()

        except Exception as e:
            print(f"连接数据库失败，错误为: {e}，请检查参数配置或连接！")

    # 获取连接connect
    def get_connect(self):
        return self._conn

    # 获取游标cursor
    def get_cursor(self):
        return self._cursor

    # 关闭数据库连接
    def close_db(self):
        if self._cursor:
            self._cursor.close()
        if self._conn:
            self._conn.close()

    # 创建新数据库
    def create_db(self, db_name):
        try:
            self._cursor.execute(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 {db_name} 创建成功!")

        except Error as e:
            self.close_db()
            print(f"创建数据库失败，发生错误: {e}!")

    # 选择数据库
    def select_db(self, db_name):
        try:
            self._cursor.execute(f"USE {db_name}")
            print(f"正在操作数据库:{db_name}")

        except Error as e:
            self.close_db()
            print(f"选择数据库{db_name}失败，发生错误: {e}!")

    # 创建表
    def create_table(self, table_name, field):
        try:
            self._cursor.execute(f"CREATE TABLE `{table_name}` ({field}) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print(f"表 {table_name} 创建成功!")

        except Error as e:
            self.close_db()
            print(f"创建表失败，发生错误: {e}!")

    def execute_sql(self, sql, isNeed=False):
        if isNeed:
            try:
                # 执行
                self._cursor.execute(sql)
                result = self._cursor.fetchall()
                # print(f"查询成功，共计{self._cursor.rowcount}行！")
                return result

            except Error as e:
                print(f"发生错误: {e}，执行回滚！")
                self._conn.rollback()
                self.close_db()
                return None

        else:
            self._cursor.execute(sql)
            result = self._cursor.fetchall()
            # print(f"查询成功，返回{self._cursor.rowcount}行！")
            return result

    # 执行sql语句 isNeed为是否需要回滚
    def execute(self, sql: str, data: tuple = None, isNeed=True):
        if isNeed:
            try:
                # 执行
                self._cursor.execute(sql, data)
                # 提交
                self._conn.commit()
                # print(f"执行成功，影响{self._cursor.rowcount}行！")

            except Error as e:
                print(f"发生错误: {e}，执行回滚！")
                self._conn.rollback()
                self.close_db()

        else:
            self._cursor.execute(sql, data)
            self._conn.commit()

    """
        SELECT column1, column2, ...
        FROM table_name
        [WHERE condition]
        [ORDER BY column_name [ASC | DESC]]
        [LIMIT number];
    """

    # 查询单条数据
    def select_one(self, table_name: str, columns: str = '*', conditions: dict = None):
        sql = f"SELECT {columns} FROM {table_name}"

        # 构建WHERE字句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        try:
            # print(sql)
            self._cursor.execute(sql, params)
            result = self._cursor.fetchone()
            return result

        except Error as e:
            print(f"查询失败，发生错误：{e}")
            self.close_db()
            return -1

    # 查询多条数据
    def select_all(self, table_name: str, columns: str = '*', conditions: dict = None, order_by: str = None,
                   order_direction: str = 'ASC', limit: int = None):

        sql = f"SELECT {columns} FROM `{table_name}`"

        # 构建 WHERE 子句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        # 构建 ORDER BY 子句
        if order_by:
            sql += f" ORDER BY {order_by}"
            if order_direction:
                sql += f" {order_direction}"

        # 添加 LIMIT 子句
        if limit:
            sql += f" LIMIT {limit}"

        try:
            # 执行查询
            self._cursor.execute(sql, params)
            # 获取查询结果
            result = self._cursor.fetchall()  # 使用 fetchall() 因为可能返回多条记录
            return result

        except Error as e:
            print(f"查询失败，发生错误: {e}")
            self.close_db()
            return -1

    """
    INSERT INTO table_name (column1, column2, column3, ...) VALUES (value1, value2, value3, ...);
    """

    # 插入单条数据
    def insert_one(self, table_name, data: dict):
        sql = "INSERT INTO `{}` ({}) VALUES ({})".format(
            table_name,
            ", ".join(data.keys()),
            ", ".join(["%s"] * len(data))
        )

        self.execute(sql, tuple(data.values()), isNeed=True)

    # 插入多条数据
    def insert_all(self, table_name, datas):
        try:
            # 确保datas中所有字典的键顺序一致
            keys = list(datas[0].keys())
            # 构建SQL语句
            sql = "INSERT INTO `{}` ({}) VALUES ({})".format(
                table_name,
                ", ".join(keys),
                ", ".join(["%s"] * len(list(datas[0].keys()))))

            # 准备数据，每个字典的值按照keys的顺序排列
            values_list = [tuple(data[key] for key in keys) for data in datas]

            # 执行插入操作
            self._cursor.executemany(sql, values_list)
            self._conn.commit()

            # print(f"插入成功，共计插入{self._cursor.rowcount}行！")

        except Error as e:
            # 发生异常时回滚事务
            self._conn.rollback()
            self.close_db()
            print(f"插入失败，发生错误：{e}")

    """
    UPDATE table_name
    SET column1 = value1, column2 = value2, ...
    WHERE condition;
    """

    # 更新单条数据
    def update_one(self, table_name: str, data: dict, condition: str):
        # 创建SET语句
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE `{table_name}` SET {set_clause} WHERE {condition}"

        self.execute(sql, tuple(data.values()), isNeed=True)

    """    
    DELETE FROM table_name
    WHERE condition;
    """

    # 删除数据
    def delete_data(self, table_name: str, condition: str = None):
        sql = f"DELETE FROM `{table_name}`"
        if condition:
            sql += f"WHERE {condition}"

        self.execute(sql, isNeed=True)

    """
    每个表的增删改查方法
    """

    # 智能体表
    def agent_insert(self, agent_inf: dict):
        """
        Args:
            agent_inf (dict): 插入的字段和数据
            Tsingshan_info = {
                'agent_id': 1, # 智能体编号
                'agent_name': 'Tsingshan', # 智能体名称
                'agent_type': 'major player' / 'retail investor', # 智能体类型 资金大头/个体散户
                'agent_info': '青山集团',
                'init_fund': 1000000
            }

        Returns:
            (int):成功返回0(非自增)或者id(id自增) 失败则返回-1
        """
        sql = "INSERT INTO `agent` ({}) VALUES ({})".format(
            ", ".join(agent_inf.keys()),
            ", ".join(["%s"] * len(agent_inf))
        )

        try:
            self._cursor.execute(sql, tuple(agent_inf.values()))
            self._conn.commit()
            # print(f"插入成功，共计插入{self._cursor.rowcount}行！")
            return self._cursor.lastrowid

        except Error as e:
            print(f"插入失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def agent_delete(self, condition=None):
        """
        Args:
            condition (str, optional): 所要删除条目的条件 默认为空
            "agent_name = 'Tsingshan'"

        Returns:
            (int): 成功返回0 失败返回-1
        """
        sql = f"DELETE FROM `agent`"
        if condition:
            sql += f"WHERE {condition}"

        try:
            self._cursor.execute(sql)
            self._conn.commit()
            print(f"删除成功，共计删除{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"删除失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def agent_update(self, data: dict, condition: str):
        """
        Args:
            data (dict): 所要更新的属性和值
            condition (str): 更新筛选条件

        Returns:
            (int): 成功返回0 失败返回-1
        """
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE `agent` SET {set_clause} WHERE {condition}"

        try:
            self._cursor.execute(sql, tuple(data.values()))
            self._conn.commit()
            # print(f"更新成功，共计影响{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"更新失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def agent_select(self, columns: str = '*', conditions: dict = None, order_by: str = None,
                     order_direction: str = 'ASC', limit: int = None):
        """
        Args:
            columns (str, optional): 查询的属性 默认为 '*'.
            conditions (dict, optional): 查询的条件 默认为空
            order_by (str, optional): 按哪个属性进行排序 默认为空
            order_direction (str, optional): 正序'ASC'还是倒序'DESC' 默认为'ASC'.
            limit (int, optional): 查询条目数目限制 默认为空

        Returns:
            (Dict/int): 成功返回查询到的所有条目 失败返回-1
        """
        sql = f"SELECT {columns} FROM `agent`"

        # 构建 WHERE 子句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        # 构建 ORDER BY 子句
        if order_by:
            sql += f" ORDER BY {order_by}"
            if order_direction:
                sql += f" {order_direction}"

        # 添加 LIMIT 子句
        if limit:
            sql += f" LIMIT {limit}"

        try:
            # 执行查询
            self._cursor.execute(sql, params)
            # 获取查询结果
            result = self._cursor.fetchall()
            # print(f"查询成功，共找到符合条件的{self._cursor.rowcount}行！")
            return result

        except Error as e:
            print(f"查询失败，发生错误: {e}")
            self.close_db()
            return -1

    # 智能体回合信息记录表
    def agent_record_insert(self, agent_record_inf: dict):
        """
        Args:
            agent_record_inf (dict): 智能体回合记录信息
            agent_record_inf = {
                'agent_record_id': 001, # 记录编号
                'agent_id': 1, # 智能体编号
                'round': 1, # 回合数
                'current_funds': 1000000.00, # 当前资金
                'valid_funds': 1000000.00, # 可用资金
                'profit_loss': 0.00, # 盈亏金额
            }

        Returns:
            _type_: _description_
        """
        sql = "INSERT INTO `agent_record` ({}) VALUES ({})".format(
            ", ".join(agent_record_inf.keys()),
            ", ".join(["%s"] * len(agent_record_inf))
        )

        try:
            self._cursor.execute(sql, tuple(agent_record_inf.values()))
            self._conn.commit()
            # print(f"插入成功，共计插入{self._cursor.rowcount}行！")
            return self._cursor.lastrowid

        except Error as e:
            print(f"插入失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def agent_record_delete(self, condition=None):

        sql = f"DELETE FROM `agent_record`"
        if condition:
            sql += f"WHERE {condition}"

        try:
            self._cursor.execute(sql)
            self._conn.commit()
            # print(f"删除成功，共计删除{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"删除失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def agent_record_update(self, data: dict, condition: str):

        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE `agent_record` SET {set_clause} WHERE {condition}"

        try:
            self._cursor.execute(sql, tuple(data.values()))
            self._conn.commit()
            # print(f"更新成功，共计影响{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"更新失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def agent_record_select(self, columns: str = '*', conditions: dict = None, order_by: str = None,
                            order_direction: str = 'ASC', limit: int = None):
        sql = f"SELECT {columns} FROM `agent_record`"

        # 构建 WHERE 子句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        # 构建 ORDER BY 子句
        if order_by:
            sql += f" ORDER BY {order_by}"
            if order_direction:
                sql += f" {order_direction}"

        # 添加 LIMIT 子句
        if limit:
            sql += f" LIMIT {limit}"

        try:
            # 执行查询
            self._cursor.execute(sql, params)
            # 获取查询结果
            result = self._cursor.fetchall()
            # print(f"查询成功，共找到符合条件的{self._cursor.rowcount}行！")
            return result

        except Error as e:
            print(f"查询失败，发生错误: {e}")
            self.close_db()
            return -1

            # 期货合约表

    def futures_insert(self, futures_inf: dict):
        """
        Args:
            futures_inf (dict): 期货合约信息
            futures_inf = {
                'futures_id': 1, # 期货合约id
                'futures_name': 'Ni2409', # 期货合约名称
                'commodity': 'Ni', # 期货合约商品
                'init_price': 10000, # 初始价格
                'price_limit': 0.04, # 价格浮动比例
                'margin_rate': 0.5, # 保证金比例
                'contract_round': 10 # 最迟交割回合
            }
        Returns:
            (int): 成功返回0 失败返回-1
        """
        sql = "INSERT INTO `futures` ({}) VALUES ({})".format(
            ", ".join(futures_inf.keys()),
            ", ".join(["%s"] * len(futures_inf))
        )

        try:
            self._cursor.execute(sql, tuple(futures_inf.values()))
            self._conn.commit()
            # print(f"插入成功，共计插入{self._cursor.rowcount}行！")
            return self._cursor.lastrowid

        except Error as e:
            print(f"插入失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def futures_delete(self, condition=None):

        sql = f"DELETE FROM `futures`"
        if condition:
            sql += f"WHERE {condition}"

        try:
            self._cursor.execute(sql)
            self._conn.commit()
            # print(f"删除成功，共计删除{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"删除失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def futures_update(self, data: dict, condition: str):

        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE `futures` SET {set_clause} WHERE {condition}"

        try:
            self._cursor.execute(sql, tuple(data.values()))
            self._conn.commit()
            # print(f"更新成功，共计影响{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"更新失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def futures_select(self, columns: str = '*', conditions: dict = None, order_by: str = None,
                       order_direction: str = 'ASC', limit: int = None):
        sql = f"SELECT {columns} FROM `futures`"

        # 构建 WHERE 子句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        # 构建 ORDER BY 子句
        if order_by:
            sql += f" ORDER BY {order_by}"
            if order_direction:
                sql += f" {order_direction}"

        # 添加 LIMIT 子句
        if limit:
            sql += f" LIMIT {limit}"

        try:
            # 执行查询
            self._cursor.execute(sql, params)
            # 获取查询结果
            result = self._cursor.fetchall()
            # print(f"查询成功，共找到符合条件的{self._cursor.rowcount}行！")
            return result

        except Error as e:
            print(f"查询失败，发生错误: {e}")
            self.close_db()
            return -1

    # 期货合约回合信息记录表
    def futures_record_insert(self, futures_record_inf: dict):
        """
        Args:
            futures_record_inf (dict): 期货合约回合信息记录表
            futures_record_inf = {
                'futures_record_id': 001, # 记录编号
                'futures_id': 1, # 期货合约id
                'round': 1, # 回合数
                'bid_price': 10000, # 买入价格
                'ask_price': 10000, # 卖出价格
                'opening_price': 10000, # 开盘价格
                'closing_price': 10000, # 收盘价格
                'settlement_price': 10000 # 结算价格
            }

        Returns:
            _type_: _description_
        """
        sql = "INSERT INTO `futures_record` ({}) VALUES ({})".format(
            ", ".join(futures_record_inf.keys()),
            ", ".join(["%s"] * len(futures_record_inf))
        )

        try:
            self._cursor.execute(sql, tuple(futures_record_inf.values()))
            self._conn.commit()
            # print(f"插入成功，共计插入{self._cursor.rowcount}行！")
            return self._cursor.lastrowid

        except Error as e:
            print(f"插入失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def futures_record_delete(self, condition=None):

        sql = f"DELETE FROM `futures_record`"
        if condition:
            sql += f"WHERE {condition}"

        try:
            self._cursor.execute(sql)
            self._conn.commit()
            # print(f"删除成功，共计删除{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"删除失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def futures_record_update(self, data: dict, condition: str):

        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE `futures_record` SET {set_clause} WHERE {condition}"

        try:
            self._cursor.execute(sql, tuple(data.values()))
            self._conn.commit()
            # print(f"更新成功，共计影响{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"更新失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def futures_record_select(self, columns: str = '*', conditions: dict = None, order_by: str = None,
                              order_direction: str = 'ASC', limit: int = None):
        sql = f"SELECT {columns} FROM `futures_record`"

        # 构建 WHERE 子句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        # 构建 ORDER BY 子句
        if order_by:
            sql += f" ORDER BY {order_by}"
            if order_direction:
                sql += f" {order_direction}"

        # 添加 LIMIT 子句
        if limit:
            sql += f" LIMIT {limit}"

        try:
            # 执行查询
            self._cursor.execute(sql, params)
            # 获取查询结果
            result = self._cursor.fetchall()
            # print(f"查询成功，共找到符合条件的{self._cursor.rowcount}行！")
            return result

        except Error as e:
            print(f"查询失败，发生错误: {e}")
            self.close_db()
            return -1

    # 订单表
    def order_insert(self, order_inf: dict):
        """
        Args:
            order_inf (dict): 订单信息
            order_inf = {
                'order_id': 1, # 订单编号
                'agent_id': 1, # 下单智能体编号
                'futures_id': 1, # 下单期货合约编号
                'order_type': 'buy' / 'sell', # 订单类型 买多 / 卖空
                'order_price': 100000, # 订单价格
                'order_lots': 10, # 订单手数
                'order_round': 1, # 下单回合
                'order_status': 'pending' / 'cancel' / 'done' / 'close', # 订单状态 挂起/撤销/成交/关闭
            }

        Returns:
            _type_: _description_
        """
        sql = "INSERT INTO `order` ({}) VALUES ({})".format(
            ", ".join(order_inf.keys()),
            ", ".join(["%s"] * len(order_inf))
        )

        try:
            self._cursor.execute(sql, tuple(order_inf.values()))
            self._conn.commit()
            # print(f"插入成功，共计插入{self._cursor.rowcount}行！")
            return self._cursor.lastrowid

        except Error as e:
            print(f"插入失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def order_delete(self, condition=None):

        sql = f"DELETE FROM `order`"
        if condition:
            sql += f"WHERE {condition}"

        try:
            self._cursor.execute(sql)
            self._conn.commit()
            # print(f"删除成功，共计删除{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"删除失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def order_update(self, data: dict, condition: str):

        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE `order` SET {set_clause} WHERE {condition}"

        try:
            self._cursor.execute(sql, tuple(data.values()))
            self._conn.commit()
            # print(f"更新成功，共计影响{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"更新失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def order_select(self, columns: str = '*', conditions: dict = None, order_by: str = None,
                     order_direction: str = 'ASC', limit: int = None):
        sql = f"SELECT {columns} FROM `order`"

        # 构建 WHERE 子句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        # 构建 ORDER BY 子句
        if order_by:
            sql += f" ORDER BY {order_by}"
            if order_direction:
                sql += f" {order_direction}"

        # 添加 LIMIT 子句
        if limit:
            sql += f" LIMIT {limit}"

        try:
            # 执行查询
            self._cursor.execute(sql, params)
            # 获取查询结果
            result = self._cursor.fetchall()
            # print(f"查询成功，共找到符合条件的{self._cursor.rowcount}行！")
            return result

        except Error as e:
            print(f"查询失败，发生错误: {e}")
            self.close_db()
            return -1

    # 现货表
    def actuals_insert(self, actuals_inf: dict):
        """
        Args:
            actuals_inf (dict): 现货信息表
            actuals_inf = {
                'actuals_id': 1, # 现货商品id
                'actuals_name': 'Ni', # 现货商品名称
                'actuals_price': 100000, # 现货商品价格
                'current_round': 1, # 当前回合
            }

        Returns:
            _type_: _description_
        """
        sql = "INSERT INTO `actuals` ({}) VALUES ({})".format(
            ", ".join(actuals_inf.keys()),
            ", ".join(["%s"] * len(actuals_inf))
        )

        try:
            self._cursor.execute(sql, tuple(actuals_inf.values()))
            self._conn.commit()
            # print(f"插入成功，共计插入{self._cursor.rowcount}行！")
            return self._cursor.lastrowid

        except Error as e:
            print(f"插入失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def actuals_delete(self, condition=None):

        sql = f"DELETE FROM `actuals`"
        if condition:
            sql += f"WHERE {condition}"

        try:
            self._cursor.execute(sql)
            self._conn.commit()
            # print(f"删除成功，共计删除{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"删除失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def actuals_update(self, data: dict, condition: str):

        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE `actuals` SET {set_clause} WHERE {condition}"

        try:
            self._cursor.execute(sql, tuple(data.values()))
            self._conn.commit()
            # print(f"更新成功，共计影响{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"更新失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def actuals_select(self, columns: str = '*', conditions: dict = None, order_by: str = None,
                       order_direction: str = 'ASC', limit: int = None):
        sql = f"SELECT {columns} FROM `actuals`"

        # 构建 WHERE 子句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        # 构建 ORDER BY 子句
        if order_by:
            sql += f" ORDER BY {order_by}"
            if order_direction:
                sql += f" {order_direction}"

        # 添加 LIMIT 子句
        if limit:
            sql += f" LIMIT {limit}"

        try:
            # 执行查询
            self._cursor.execute(sql, params)
            # 获取查询结果
            result = self._cursor.fetchall()
            # print(f"查询成功，共找到符合条件的{self._cursor.rowcount}行！")
            return result

        except Error as e:
            print(f"查询失败，发生错误: {e}")
            self.close_db()
            return -1

    # 订单成交表
    def deal_record_insert(self, deal_record_inf: dict):
        """
        Args:
            deal_record_inf (dict): 订单成交记录信息
            deal_record_inf = {
                'deal_record_id': 1, # 订单成交记录编号
                'bid_order_id': 1, # 买方订单编号
                'sell_order_id': 2, # 卖方订单编号
                'deal_lots': 10, # 成交手数
                'deal_price': 100000, # 成交价格
                'deal_round': 2, # 成交回合
                'delivery_round': 10, # 平仓/交割回合
            }

        Returns:
            _type_: _description_
        """
        sql = "INSERT INTO `deal_record` ({}) VALUES ({})".format(
            ", ".join(deal_record_inf.keys()),
            ", ".join(["%s"] * len(deal_record_inf))
        )

        try:
            self._cursor.execute(sql, tuple(deal_record_inf.values()))
            self._conn.commit()
            # print(f"插入成功，共计插入{self._cursor.rowcount}行！")
            return self._cursor.lastrowid

        except Error as e:
            print(f"插入失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def deal_record_delete(self, condition=None):

        sql = f"DELETE FROM `deal_record`"
        if condition:
            sql += f"WHERE {condition}"

        try:
            self._cursor.execute(sql)
            self._conn.commit()
            # print(f"删除成功，共计删除{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"删除失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def deal_record_update(self, data: dict, condition: str):

        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE `deal_record` SET {set_clause} WHERE {condition}"

        try:
            self._cursor.execute(sql, tuple(data.values()))
            self._conn.commit()
            # print(f"更新成功，共计影响{self._cursor.rowcount}行！")
            return 0

        except Error as e:
            print(f"更新失败，错误原因为：{e}")
            self._conn.rollback()
            self.close_db()
            return -1

    def deal_record_select(self, columns: str = '*', conditions: dict = None, order_by: str = None,
                           order_direction: str = 'ASC', limit: int = None):
        sql = f"SELECT {columns} FROM `deal_record`"

        # 构建 WHERE 子句
        if conditions:
            sql += " WHERE " + " AND ".join([f"{k} = %s" for k in conditions.keys()])
            params = tuple(conditions.values())
        else:
            params = ()

        # 构建 ORDER BY 子句
        if order_by:
            sql += f" ORDER BY {order_by}"
            if order_direction:
                sql += f" {order_direction}"

        # 添加 LIMIT 子句
        if limit:
            sql += f" LIMIT {limit}"

        try:
            # 执行查询
            self._cursor.execute(sql, params)
            # 获取查询结果
            result = self._cursor.fetchall()
            # print(f"查询成功，共找到符合条件的{self._cursor.rowcount}行！")
            return result

        except Error as e:
            print(f"查询失败，发生错误: {e}")
            self.close_db()
            return -1
