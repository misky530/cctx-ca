import asyncio
import json
import time

import ccxt
import redis

# # 创建一个 Coinbase 交易所对象
# exchange = ccxt.coinbase({
#     'proxies': {
#         'http': 'http://127.0.0.1:7890',
#         'https': 'http://127.0.0.1:7890',
#     },
# })

coinbase_exchange = ccxt.coinbase({
    'proxies': {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890',
    },
})

binance_exchange = ccxt.coinbase({
    'proxies': {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890',
    },
})

# 定义获取 ticker 数据的函数
completed = 0  # 已完成的请求数
lock = asyncio.Lock()  # 用于线程安全的输出

# 连接到 Redis
redis_client = redis.StrictRedis(host='36.137.225.245', port=6376, db=1, password='mtic0756-dev')

redis_key_prefix = 'tt'


def fetch_ticker(symbol):
    global completed
    try:
        key = f"{redis_key_prefix}:{symbol}"
        # 尝试从 Redis 获取缓存数据
        cached_ticker = redis_client.get(key)
        if cached_ticker:
            ticker = json.loads(cached_ticker)
            completed += 1
            print(f"Fetched from Redis {completed}: {key}")
            return ticker

        # 如果缓存不存在或已过期，调用 API 获取数据
        ticker = coinbase_exchange.fetch_ticker(symbol)
        # 将 ticker 数据存储到 Redis 中，使用 key 作为键，设置 TTL 为 1 小时
        redis_client.setex(key, 3600, json.dumps(ticker))
        completed += 1
        print(f"Fetched from API {completed}: {key}")
        return ticker
    except Exception as e:
        completed += 1
        print(f"Error fetching ticker for {key}: {e}. Progress: {completed}")
        return None


def calculate_gas_cost(transaction_type):
    # 这里假设每次交易的gas费用是固定的，你可以根据实际情况调整
    gas_costs = {
        'buy': 0.00064,  # 假设买入的gas费用是10美元
        'sell': 0.00064  # 假设卖出的gas费用是10美元
    }
    return gas_costs.get(transaction_type, 0)


def main():
    global completed

    # 加载所有交易所的市场信息，并筛选出以 USDT 为计价单位的交易对
    markets = coinbase_exchange.load_markets()
    usdt_symbols = [symbol for symbol in markets if symbol.endswith('/USDT')]

    print(usdt_symbols)

    # 开始时间
    start_time = time.time()

    # 获取所有交易所的 ticker 数据
    tickers = []

    for symbol in usdt_symbols:
        ticker = fetch_ticker(symbol)
        if ticker:
            tickers.append(ticker)

    # 结束时间
    end_time = time.time()

    # 计算耗时
    elapsed_time = end_time - start_time

    # 过滤出有效的 ticker 数据
    valid_tickers = [ticker for ticker in tickers if ticker]

    # 只保留以 USDT 为计价单位的交易对
    usdt_tickers = [ticker for ticker in valid_tickers if ticker['symbol'].endswith('/USDT')]

    # 使用 baseVolume 排序，如果 baseVolume 不存在，则使用 last 价
    sorted_tickers = sorted(
        usdt_tickers,
        key=lambda x: (x['baseVolume'] if x['baseVolume'] is not None else 0, x['last']),
        reverse=True
    )
    top_10_tickers = sorted_tickers[:10]

    # 打印结果
    print("\nTop 10 most active USDT trading pairs:")
    for ticker in top_10_tickers:
        symbol = ticker['symbol']
        base_volume = ticker['baseVolume']
        last_price = ticker['last']
        print(f"Trading Pair: {symbol}, Base Volume: {base_volume}, Last Price: {last_price}")

    # 打印耗时
    print(f"\nTime taken to fetch data: {elapsed_time:.2f} seconds")

    # 获取 CoinBase 上的实时价格
    print("\nReal-time prices on Coinbase for the top 10 USDT trading pairs:")
    coinbase_prices = {}
    for ticker in top_10_tickers:
        symbol = ticker['symbol']
        base_currency = symbol.split('/')[0]  # 获取基础货币
        coinbase_symbol = f"{base_currency}/USD"  # Coinbase 上的交易对

        if coinbase_symbol in coinbase_exchange.markets:
            try:
                coinbase_ticker = coinbase_exchange.fetch_ticker(coinbase_symbol)
                coinbase_price = coinbase_ticker['last']
                coinbase_prices[symbol] = coinbase_price
                # 将科学计数法转换为标准格式
                formatted_price = f"{coinbase_price:.8f}"
                print(f"Coinbase {coinbase_symbol} price: {formatted_price}")
            except Exception as e:
                print(f"Error fetching price for {coinbase_symbol} on Coinbase: {e}")
        else:
            print(f"{coinbase_symbol} is not available on Coinbase.")

    # 获取 Binance 上的实时价格并对比差价
    binance_exchange.load_markets()
    price_differences = []
    print("\nReal-time prices on Binance and price differences for the top 10 USDT trading pairs:")
    for ticker in top_10_tickers:
        symbol = ticker['symbol']
        if symbol in binance_exchange.markets:
            try:
                binance_ticker = binance_exchange.fetch_ticker(symbol)
                binance_price = binance_ticker['last']
                # 将科学计数法转换为标准格式
                formatted_price = f"{binance_price:.8f}"
                print(f"Binance {symbol} price: {formatted_price}")

                # 对比差价
                if symbol in coinbase_prices:
                    coinbase_price = coinbase_prices[symbol]
                    price_difference = abs(binance_price - coinbase_price)
                    price_differences.append((symbol, price_difference, binance_price, coinbase_price))
            except Exception as e:
                print(f"Error fetching price for {symbol} on Binance: {e}")
        else:
            print(f"{symbol} is not available on Binance.")

    # 按差价从大到小排序
    sorted_price_differences = sorted(price_differences, key=lambda x: x[1], reverse=True)

    # 打印差价排序结果
    print("\nPrice differences between Binance and Coinbase (sorted from largest to smallest):")
    for symbol, price_difference, binance_price, coinbase_price in sorted_price_differences:
        # 计算买入和卖出的gas费用
        buy_gas_cost = calculate_gas_cost('buy')
        sell_gas_cost = calculate_gas_cost('sell')

        # 假设买入数量为 1 个单位的基础货币
        buy_amount = 1.0
        total_cost = buy_amount * binance_price + buy_gas_cost
        total_revenue = buy_amount * coinbase_price - sell_gas_cost
        profit = total_revenue - total_cost

        print(
            f"Trading Pair: {symbol}, Price Difference: {price_difference:.8f}, Binance Price: {binance_price:.8f}, Coinbase Price: {coinbase_price:.8f}, Profit: {profit:.8f}")


# 运行主函数
if __name__ == "__main__":
    main()
