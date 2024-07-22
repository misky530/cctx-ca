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

exchanges = {
    'coinbasepro': ccxt.coinbase({
        'proxies': {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890',
        },
    }),
    # 'binance': ccxt.binance({
    #     'proxies': {
    #         'http': 'http://127.0.0.1:7890',
    #         'https': 'http://127.0.0.1:7890',
    #     },
    # }),
}

# 定义获取 ticker 数据的函数
completed = 0  # 已完成的请求数
lock = asyncio.Lock()  # 用于线程安全的输出

# 连接到 Redis
redis_client = redis.StrictRedis(host='36.137.225.245', port=6376, db=1, password='mtic0756-dev')


def fetch_ticker(exchange_id, exchange, symbol):
    global completed
    try:
        key = f"{exchange_id}:{symbol}"
        # 尝试从 Redis 获取缓存数据
        cached_ticker = redis_client.get(key)
        if cached_ticker:
            ticker = json.loads(cached_ticker)
            completed += 1
            print(f"Fetched from Redis {completed}: {key}")
            return ticker

        # 如果缓存不存在或已过期，调用 API 获取数据
        ticker = exchange.fetch_ticker(symbol)
        # 将 ticker 数据存储到 Redis 中，使用 key 作为键，设置 TTL 为 1 小时
        redis_client.setex(key, 3600, json.dumps(ticker))
        completed += 1
        print(f"Fetched from API {completed}: {key}")
        return ticker
    except Exception as e:
        completed += 1
        print(f"Error fetching ticker for {key}: {e}. Progress: {completed}")
        return None


def main():
    global completed
    usdt_symbols = {}

    # 加载所有交易所的市场信息，并筛选出以 USDT 为计价单位的交易对
    for exchange_id, exchange in exchanges.items():
        markets = exchange.load_markets()
        usdt_symbols[exchange_id] = [symbol for symbol in markets if symbol.endswith('/USDT')]

    # 开始时间
    start_time = time.time()

    # 获取所有交易所的 ticker 数据
    tickers = []
    for exchange_id, symbols in usdt_symbols.items():
        for symbol in symbols:
            ticker = fetch_ticker(exchange_id, exchange, symbol)
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
    coinbasepro = exchanges['coinbasepro']
    coinbasepro.load_markets()
    print("\nReal-time prices on Coinbase for the top 10 USDT trading pairs:")
    for ticker in top_10_tickers:
        symbol = ticker['symbol']
        base_currency = symbol.split('/')[0]  # 获取基础货币
        coinbase_symbol = f"{base_currency}/USD"  # Coinbase 上的交易对

        if coinbase_symbol in coinbasepro.markets:
            try:
                coinbase_ticker = coinbasepro.fetch_ticker(coinbase_symbol)
                coinbase_price = coinbase_ticker['last']
                # 将科学计数法转换为标准格式
                formatted_price = f"{coinbase_price:.8f}"
                print(f"Coinbase {coinbase_symbol} price: {formatted_price}")
            except Exception as e:
                print(f"Error fetching price for {coinbase_symbol} on Coinbase: {e}")
        else:
            print(f"{coinbase_symbol} is not available on Coinbase.")


# 运行主函数
if __name__ == "__main__":
    main()
