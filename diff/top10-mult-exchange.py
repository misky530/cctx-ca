import asyncio
import json
import time

import ccxt.async_support as ccxt
import redis

proxy = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890',
}

redis_conn_str = "redis://localhost"

# 定义支持的交易所
exchanges = {
    'coinbasepro': ccxt.coinbase({
        'proxies': {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890',
        },
    }),
    'binance': ccxt.binance({
        'proxies': {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890',
        },
    }),
}


# 加载市场信息
async def load_markets(exchange):
    return await exchange.load_markets()


# 定义获取 ticker 数据的函数
completed = 0  # 已完成的请求数
lock = asyncio.Lock()  # 用于线程安全的输出

# 连接到 Redis
redis_client = redis.from_url("redis://36.137.225.245;db=1;password=mtic0756-dev")


async def fetch_ticker(exchange_id, exchange, symbol):
    global completed
    try:
        key = f"{exchange_id}:{symbol}"
        # 尝试从 Redis 获取缓存数据
        cached_ticker = await redis_client.get(key)
        if cached_ticker:
            ticker = json.loads(cached_ticker)
            async with lock:
                completed += 1
                print(f"Fetched from Redis {completed}: {key}")
            return ticker

        # 如果缓存不存在或已过期，调用 API 获取数据
        ticker = await exchange.fetch_ticker(symbol)
        # 将 ticker 数据存储到 Redis 中，使用 key 作为键，设置 TTL 为 1 小时
        await redis_client.setex(key, 3600, json.dumps(ticker))
        async with lock:
            completed += 1
            print(f"Fetched from API {completed}: {key}")
        return ticker
    except Exception as e:
        async with lock:
            completed += 1
            print(f"Error fetching ticker for {key}: {e}. Progress: {completed}")
        return None


async def main():
    global completed
    all_symbols = {}

    # 加载所有交易所的市场
    for exchange_id, exchange in exchanges.items():
        markets = await load_markets(exchange)
        all_symbols[exchange_id] = list(markets.keys())

    # 开始时间
    start_time = time.time()

    # 并行获取所有交易所的 ticker 数据
    tasks = [
        fetch_ticker(exchange_id, exchange, symbol)
        for exchange_id, symbols in all_symbols.items()
        for symbol in symbols
    ]
    tickers = await asyncio.gather(*tasks)

    # 结束时间
    end_time = time.time()

    # 计算耗时
    elapsed_time = end_time - start_time

    # 过滤出有效的 ticker 数据，按交易量排序并获取前 10 名
    valid_tickers = [ticker for ticker in tickers if ticker]
    top_10_tickers = sorted(valid_tickers, key=lambda x: x['quoteVolume'], reverse=True)[:10]

    # 打印结果
    print("\nTop 10 most active trading pairs by volume:")
    for ticker in top_10_tickers:
        symbol = ticker['symbol']
        volume = ticker['quoteVolume']
        print(f"Trading Pair: {symbol}, Volume: {volume}")

    # 打印耗时
    print(f"\nTime taken to fetch data: {elapsed_time:.2f} seconds")


if __name__ == '__main__':
    # 运行主函数
    asyncio.run(main())
