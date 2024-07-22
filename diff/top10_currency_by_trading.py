import concurrent.futures
import json
import threading
import time

import ccxt
import redis

# 创建一个 Coinbase 交易所对象
exchange = ccxt.coinbase({
    'proxies': {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890',
    },
})

# 获取市场信息
markets = exchange.load_markets()
print(f'Coinbase 支持的交易对数量: {len(markets)}')

# 定义获取ticker数据的函数
lock = threading.Lock()  # 用于线程安全的输出
completed = 0  # 已完成的请求数

# 连接到 Redis
redis_client = redis.StrictRedis(host='36.137.225.245', port=6376, db=1, password='mtic0756-dev')


def fetch_ticker(symbol):
    global completed
    try:
        # 尝试从 Redis 获取缓存数据
        cached_ticker = redis_client.get(symbol)
        if cached_ticker:
            ticker = json.loads(cached_ticker)
            with lock:
                completed += 1
                print(f"Fetched from Redis {completed}/{len(symbols)}: {symbol}")
            return ticker

        # 如果缓存不存在或已过期，调用 API 获取数据
        ticker = exchange.fetch_ticker(symbol)
        # 将 ticker 数据存储到 Redis 中，使用 symbol 作为键，设置 TTL 为 1 小时
        redis_client.setex(symbol, 3600, json.dumps(ticker))
        with lock:
            completed += 1
            print(f"Fetched from API {completed}/{len(symbols)}: {symbol}")
        return ticker
    except Exception as e:
        with lock:
            completed += 1
            print(f"Error fetching ticker for {symbol}: {e}. Progress: {completed}/{len(symbols)}")
        return None


# 获取所有交易对
symbols = list(markets.keys())

# 开始时间
start_time = time.time()

# 使用ThreadPoolExecutor并行获取ticker数据
tickers = []
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    future_to_symbol = {executor.submit(fetch_ticker, symbol): symbol for symbol in symbols}
    for future in concurrent.futures.as_completed(future_to_symbol):
        symbol = future_to_symbol[future]
        try:
            ticker = future.result()
            if ticker:
                tickers.append(ticker)
        except Exception as e:
            print(f"Error processing result for {symbol}: {e}")

# 结束时间
end_time = time.time()

# 计算耗时
elapsed_time = end_time - start_time

# 过滤出有效的ticker数据，按交易量排序并获取前10名
valid_tickers = [ticker for ticker in tickers if ticker]
# top_10_tickers = sorted(valid_tickers, key=lambda x: x['quoteVolume'], reverse=True)[:10]

# 使用 baseVolume 排序，如果 baseVolume 不存在，则使用 last 价
sorted_tickers = sorted(
    valid_tickers,
    key=lambda x: (x['baseVolume'] if x['baseVolume'] is not None else 0, x['last']),
    reverse=True
)
top_10_tickers = sorted_tickers[:10]

# 打印结果
print("\nTop 10 most active trading pairs:")
for ticker in top_10_tickers:
    symbol = ticker['symbol']
    base_volume = ticker['baseVolume']
    last_price = ticker['last']
    print(f"Trading Pair: {symbol}, Base Volume: {base_volume}, Last Price: {last_price}")

# 打印耗时
print(f"\nTime taken to fetch data: {elapsed_time:.2f} seconds")
