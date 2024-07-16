import ccxt


def fetch_doge_price():
    try:
        # 创建一个 Coinbase 交易所对象
        exchange = ccxt.coinbase({
            'proxies': {
                'http': 'http://127.0.0.1:7890',
                'https': 'http://127.0.0.1:7890',
            },
        })

        # 获取市场行情
        ticker = exchange.fetch_ticker('DOGE/USD')

        # 输出实时价格
        print(f"DOGE/USD 最新价格: {ticker['last']}")
    except Exception as e:
        print(f"获取价格时出错: {e}")


def fetch_doge_price_bin():
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


if __name__ == '__main__':
    fetch_doge_price()
    fetch_doge_price_bin()
