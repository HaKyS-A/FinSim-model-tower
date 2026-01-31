# 数据库连接配置
connect_config = {
    "host": "localhost",
    "port": "3306",
    "user": "<YourName>",
    "password": "<YourPwd>"
}


# 智能体表创建SQL
agent_field = """
    `agent_id` int NOT NULL,
    `agent_name` varchar(100) NULL DEFAULT NULL,
    `agent_type` enum('retail investor','major player') NOT NULL DEFAULT 'retail investor',
    `agent_info` text NULL,
    `init_fund` Decimal(30,7) NOT NULL,
    PRIMARY KEY (`agent_id`) USING BTREE
"""

# 智能体信息记录表创建SQL
agent_record_field = """
    `agent_record_id` int NOT NULL AUTO_INCREMENT,
    `agent_id` int NOT NULL,
    `round` int NOT NULL,
    `current_funds` Decimal(30,7) NOT NULL,
    `available_funds` Decimal(30,7) NOT NULL,
    `security_funds` Decimal(30,7) NULL DEFAULT NULL,
    `profit_loss` Decimal(30,7) NULL DEFAULT NULL,
    PRIMARY KEY (`agent_record_id`) USING BTREE,
    INDEX `agent_record`(`agent_id` ASC) USING BTREE,
    CONSTRAINT `agent_record` FOREIGN KEY (`agent_id`) REFERENCES `agent` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE
"""

# 期货表创建SQL
futures_field = """
    `futures_id` int NOT NULL,
    `futures_name` varchar(100) NULL DEFAULT NULL,
    `commodity` varchar(100) NOT NULL,
    `init_price` Decimal(30,7) NULL DEFAULT NULL,
    `price_limit` Decimal(30,7) NULL DEFAULT NULL,
    `margin_rate` Decimal(10,5) NULL DEFAULT NULL,
    `contract_round` int NOT NULL,
    PRIMARY KEY (`futures_id`) USING BTREE
"""

# 期货信息记录表创建SQL
futures_record_field = """   
    `futures_record_id` int NOT NULL AUTO_INCREMENT,
    `futures_id` int NOT NULL,
    `round` int NULL DEFAULT NULL,
    `settlement_price` Decimal(30,7) NULL DEFAULT NULL,
    PRIMARY KEY (`futures_record_id`) USING BTREE,
    INDEX `futures_record`(`futures_id` ASC) USING BTREE,
    CONSTRAINT `futures_record` FOREIGN KEY (`futures_id`) REFERENCES `futures` (`futures_id`) ON DELETE CASCADE ON UPDATE CASCADE
"""

# 下单表创建SQL
order_field = """
    `order_id` int NOT NULL AUTO_INCREMENT,
    `agent_id` int NOT NULL,
    `futures_id` int NOT NULL,
    `order_type` enum('buy','sell') NOT NULL,
    `order_round` int NOT NULL,
    `order_num` int NOT NULL,
    `order_price` Decimal(30,7) NOT NULL,
    `order_lots` Decimal(30,7) NOT NULL,
    `remain_lots` Decimal(30,7) NOT NULL,
    `order_status` enum('pending','cancel','done','close','invalid','no_margin') NULL DEFAULT 'pending',
    PRIMARY KEY (`order_id`) USING BTREE,
    INDEX `agent`(`agent_id` ASC) USING BTREE,
    INDEX `futures`(`futures_id` ASC) USING BTREE,
    CONSTRAINT `agent` FOREIGN KEY (`agent_id`) REFERENCES `agent` (`agent_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `futures` FOREIGN KEY (`futures_id`) REFERENCES `futures` (`futures_id`) ON DELETE CASCADE ON UPDATE CASCADE
"""

# 现货表创建SQL
actuals_field = """
    `actuals_id` int NOT NULL,
    `inventory` float NOT NULL,
    `actuals_name` varchar(100) NOT NULL,
    `current_round` int NOT NULL,
    `current_price` Decimal(30,7) NOT NULL,
    PRIMARY KEY (`actuals_id`) USING BTREE
"""

# 订单成交表创建SQL
deal_record_field = """
    `deal_id` int NOT NULL AUTO_INCREMENT,
    `bid_order_id` int NOT NULL,
    `sell_order_id` int NOT NULL,
    `deal_lots` Decimal(30,7) NOT NULL,
    `deal_price` Decimal(30,7) NOT NULL,
    `bid_status` enum('open','close','done') NOT NULL DEFAULT 'open',
    `bid_security_funds` Decimal(30,7) NOT NULL,
    `sell_status` enum('open','close','done') NOT NULL DEFAULT 'open',
    `sell_security_funds` Decimal(30,7) NOT NULL,
    `deal_round` int NOT NULL,
    `deal_num` int NOT NULL,
    `delivery_round` int NOT NULL,
    PRIMARY KEY (`deal_id`) USING BTREE,
    INDEX `bid`(`bid_order_id` ASC) USING BTREE,
    INDEX `sell`(`sell_order_id` ASC) USING BTREE,
    CONSTRAINT `bid` FOREIGN KEY (`bid_order_id`) REFERENCES `order` (`order_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `sell` FOREIGN KEY (`sell_order_id`) REFERENCES `order` (`order_id`) ON DELETE CASCADE ON UPDATE CASCADE
"""
