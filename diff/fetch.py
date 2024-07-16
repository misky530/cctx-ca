import ccxt

if __name__ == '__main__':
    # 创建一个 Binance 交易所对象
    # exchange = ccxt.binance()
    exchange = ccxt.binance({
        'proxies': {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890',
        },
    })

    # 获取市场行情
    ticker = exchange.fetch_ticker('DOGE/USDT')

    # 输出实时价格
    print(f"DOGE/USDT 最新价格: {ticker['last']}")
