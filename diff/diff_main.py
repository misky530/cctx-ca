import time

import ccxt


def get_price_difference(symbol):
    # 创建交易所实例
    binance = ccxt.binance()
    coinbase = ccxt.coinbase()

    # 获取 Binance 上的价格
    binance_ticker = binance.fetch_ticker(symbol)
    binance_price = binance_ticker['last']

    # 获取 Coinbase 上的价格
    coinbase_ticker = coinbase.fetch_ticker(symbol)
    coinbase_price = coinbase_ticker['last']

    # 计算价格差异
    price_difference = binance_price - coinbase_price
    percentage_difference = (price_difference / ((binance_price + coinbase_price) / 2)) * 100

    return binance_price, coinbase_price, price_difference, percentage_difference


def main():
    symbol = 'BTC/USDT'  # 您可以更改这个符号来比较不同的加密货币

    while True:
        try:
            binance_price, coinbase_price, price_difference, percentage_difference = get_price_difference(symbol)
            print(f"Binance {symbol} 价格: ${binance_price:.2f}")
            print(f"Coinbase {symbol} 价格: ${coinbase_price:.2f}")
            print(f"价格差异: ${price_difference:.2f}")
            print(f"百分比差异: {percentage_difference:.2f}%")
            print("-" * 30)

            # 每隔60秒更新一次
            time.sleep(60)
        except Exception as e:
            print(f"出现错误: {e}")
            break


if __name__ == "__main__":
    main()
