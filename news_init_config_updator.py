"""更具日期和期货种类更新初始化条件和新闻"""
import json

def news_update(futures_name, date_index, future_full_name, subfix):
    """
    update news.txt with new price trend and nearest 2 day news
    :param futures_name: futures_name, s.t. IH2412
    :param date_index: from 0-19
    :param future_full_name: 期货名字全称
    :param subfix: 填充第二日和第三日的默认新闻
    :return: 0 - finish update
    """
    with open(f'PricePredictionFiles/{futures_name}_price_20.json', 'r', encoding='utf-8') as f:
        prices = json.load(f)[date_index]

    with open(f'PricePredictionFiles/{futures_name}_news_list.txt', 'r', encoding='utf-8') as f:
        news = f.read().split('\n-----*****-----')

    # new news
    new_news = ''
    if date_index > 0:
        # when exist, add news of last day
        new_news = news[date_index - 1].strip()
    if new_news != news[date_index].strip():
        # add today's news
        new_news += '\n' + news[date_index].strip()

    # new price info
    prev_5_days = str(prices['prev_5_settle'])
    prev_week = ['上涨', prices['week_difference']]
    prev_month = ['上涨', prices['month_difference']]
    if prev_week[1] < 0:
        prev_week[0] = '下跌'
        prev_week[1] = -1 * prev_week[1]
    if prev_month[1] < 0:
        prev_month[0] = '下跌'
        prev_month[1] = -1 * prev_month[1]

    with open('news.txt', 'w', encoding='utf-8') as f:
        new_message = ("{fullname:s}近一周{trend_week:s}{rate_week:.2f}%，过去5个交易日结算点数为{prev_5:s}\n"
                       "{news:s}\n"
                       "数据统计显示，{fullname:s}近一个月{trend_month:s}{rate_month:.2f}%\n"
                       "-----*****-----\n{subfix:s}\n"
                       "-----*****-----\n{subfix:s}\n-----*****-----\n").format(
            fullname=future_full_name,
            trend_week=prev_week[0],
            rate_week=prev_week[1]*100,
            prev_5=prev_5_days,
            news=new_news,
            trend_month=prev_month[0],
            rate_month=prev_month[1]*100,
            subfix=subfix
        )
        f.write(new_message)
        return 0


def init_config_update(futures_name, date:str, date_index):
    """
    update Agent/configs/SystemInitConfig.json
    :param futures_name: futures_name, s.t. IH2412
    :param date: yyyy-mm-dd - str
    :param date_index: 0-19
    :return: 0 - finish
    """
    with open('Agent/configs/SystemInitConfig.json', 'r', encoding='utf-8') as f:
        current_config = json.load(f)
    with open(f'{futures_name}_price_20.json', 'r', encoding='utf-8') as f:
        prices = json.load(f)[date_index]

    current_config['initial_futures_price'] = prices['prev_5_settle'][-1]
    date_name = date.replace('-', '')
    current_config['dbname'] = f'fin_sim_futures_{futures_name}_{date_name}'
    current_config['initial_actuals_price'] = current_config['initial_futures_price'] * 0.99
    current_config['contract_round'] = 3

    with open('Agent/configs/SystemInitConfig.json', 'w', encoding='utf-8') as f:
        json.dump(current_config, f, indent=4)


if __name__ == '__main__':
    news_update('SF2503', 0, '芝加哥期货交易所大豆商品SF2503期货', '芝加哥期货交易所大豆商品SF2503期货价格总体保持稳定，在小范围内保持震荡，没有异动。')
    init_config_update('SF2503', '2024-11-04', 0)
