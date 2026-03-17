Agent = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import time
import os

# =====================================================
# API CONFIG
# =====================================================

API_URL = os.getenv("API_URL", "http://SERVER_IP:8001")
API_KEY = os.getenv("TEAM_API_KEY", "ak_e50521f02c3b140f8f9940a1df3dd57c")
HEADERS = {"X-API-Key": API_KEY}

POS_PCT   = 0.30
STOP_LOSS = 0.02

# =====================================================
# API FUNCTIONS
# =====================================================

def get_price():
    return requests.get(f"{API_URL}/api/price", headers=HEADERS, timeout=5).json()

def get_portfolio():
    return requests.get(f"{API_URL}/api/portfolio", headers=HEADERS, timeout=5).json()

def buy(qty):
    return requests.post(
        f"{API_URL}/api/buy",
        json={"quantity": qty},
        headers=HEADERS,
        timeout=5
    ).json()

def sell(qty):
    return requests.post(
        f"{API_URL}/api/sell",
        json={"quantity": qty},
        headers=HEADERS,
        timeout=5
    ).json()

# =====================================================
# LOAD TRAINING DATA
# =====================================================

df = pd.read_csv("asset_alpha_training.csv")

print(f"Rows: {len(df)}")
print(f"Price Range: {df['Close'].min()} - {df['Close'].max()}")

closes  = df['Close'].values
volumes = df['Volume'].values


# =====================================================
# FEATURE FUNCTIONS
# =====================================================

def compute_rsi(prices, period=14):

    delta = np.diff(prices)

    gain = np.maximum(delta, 0)
    loss = -np.minimum(delta, 0)

    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi = np.concatenate(([50], rsi))

    return rsi


# =====================================================
# IMPROVED STRATEGY
# =====================================================

def my_signal(closes_list, opens=None, highs=None, lows=None, volumes=None):

    if len(closes_list) < 40:
        return "hold"

    p = np.array(closes_list)

    # trend
    fast = np.mean(p[-10:])
    slow = np.mean(p[-30:])

    # momentum
    momentum = p[-1] - p[-5]

    # volatility
    vol = np.std(p[-5:])

    # volume spike
    if volumes is not None and len(volumes) > 10:
        vol_ratio = volumes[-1] / np.mean(volumes[-10:])
    else:
        vol_ratio = 1

    rsi = compute_rsi(p)[-1]

    # BUY CONDITIONS
    if fast > slow and momentum > 0 and vol_ratio > 1.2 and rsi < 70:
        return "buy"

    # SELL CONDITIONS
    if fast < slow or rsi > 75:
        return "sell"

    return "hold"


# =====================================================
# BACKTESTER
# =====================================================

def backtest(df_bt, signal_fn, pos_pct=0.30, stop=0.02, fee=0.001, cash=100000):

    closes = df_bt['Close'].values
    volumes = df_bt['Volume'].values

    hist = []

    shares = 0
    entry = None

    equity = []

    for i, price in enumerate(closes):

        hist.append(price)

        signal = signal_fn(hist, volumes=volumes[:i+1])

        # STOP LOSS
        if entry and shares > 0:
            if (price - entry) / entry < -stop:
                signal = "sell"

        # BUY
        if signal == "buy" and cash > price * 10:

            qty = int(cash * pos_pct / price)

            cost = qty * price * (1 + fee)

            if cost < cash:
                cash -= cost
                shares += qty
                entry = price

        # SELL
        elif signal == "sell" and shares > 0:

            cash += shares * price * (1 - fee)

            shares = 0
            entry = None

        total_equity = cash + shares * price

        equity.append(total_equity)

    return equity


# =====================================================
# RUN BACKTEST
# =====================================================

equity = backtest(df, my_signal)

start = equity[0]
end = equity[-1]

profit = end - start
roi = (profit / start) * 100

print("\n===== BACKTEST RESULTS =====")
print("Start Balance:", start)
print("Final Balance:", end)
print("Profit:", profit)
print("ROI:", roi, "%")

# =====================================================
# PLOT EQUITY CURVE
# =====================================================

plt.figure(figsize=(14,6))
plt.plot(equity)
plt.title("Equity Curve")
plt.xlabel("Time")
plt.ylabel("Portfolio Value")
plt.show()


# =====================================================
# LIVE TRADING LOOP
# =====================================================

def run_live():

    history = []
    entry_price = None

    while True:

        try:

            tick = get_price()
            port = get_portfolio()

            price = tick["close"]

            history.append(price)

            signal = my_signal(history)

            if entry_price and port["shares"] > 0:

                if (price - entry_price) / entry_price < -STOP_LOSS:
                    signal = "sell"

            if signal == "buy":

                qty = int(port["cash"] * POS_PCT / price)

                if qty > 0:
                    buy(qty)
                    entry_price = price
                    print("BUY", qty)

            elif signal == "sell":

                if port["shares"] > 0:
                    sell(port["shares"])
                    entry_price = None
                    print("SELL")

            print("Price:", price)

        except Exception as e:

            print("Error:", e)

        time.sleep(60)'''


with open("agent.py", "w") as f:
    f.write(AGENT.strip())

print("agent.py saved.")
print("Test it:")
print("  API_URL=http://SERVER_IP:8001 TEAM_API_KEY=your_key python agent.py")