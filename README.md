# Professional-HFT-bot-
The professional HFT bot is a bot which accesses and read the pattern of a stock about its OHLC cycle. Aftr reading it, the bot autmatically buys, sells and holds the stock to get the maximum profit. 
# Trading Agent Bot

## Overview

This project contains a **Python trading agent** that can:

-   Backtest a trading strategy on historical data
-   Analyze profitability and return on investment (ROI)
-   Plot an equity curve of portfolio performance
-   Connect to a trading API to execute live buy and sell orders

The bot uses indicators such as: - Moving averages (trend detection) -
Momentum - Volume spikes - RSI (Relative Strength Index) - Stop‑loss
risk management

------------------------------------------------------------------------

# File Structure

agent.py\
Main trading bot file. Contains: - API connection - strategy logic -
backtesting engine - optional live trading loop

asset_alpha_training.csv\
Historical price dataset used for backtesting.

README.md\
Instructions for running the bot.

------------------------------------------------------------------------

# Requirements

Install the required Python libraries:

pip install pandas numpy matplotlib requests

Python 3.8+ is recommended.

------------------------------------------------------------------------

# How To Run The Backtest

1.  Place `agent.py` and `asset_alpha_training.csv` in the same folder.

2.  Run:

python agent.py

3.  The program will output:

-   Starting balance
-   Final balance
-   Profit
-   ROI percentage

4.  A graph showing the **equity curve** will also appear.

------------------------------------------------------------------------

# Running the Bot With the API (Live Trading)

Edit the following lines in `agent.py`:

API_URL = "http://SERVER_IP:8001" API_KEY = "YOUR_KEY_HERE"

Replace them with your real API server and key.

Then enable the live trading loop by changing:

# run_live()

to

run_live()

Run the bot again:

python agent.py

The bot will then:

1.  Pull live price data
2.  Evaluate the strategy
3.  Automatically send buy/sell orders
4.  Repeat every 60 seconds

------------------------------------------------------------------------

# Strategy Logic

The trading strategy combines multiple signals:

Trend Detection\
Short moving average (10) compared to long moving average (30).

Momentum\
Price difference between the current price and recent prices.

Volume Spike Detection\
Identifies unusually high trading activity.

RSI Filter\
Avoids buying when the market is overbought.

Risk Management\
Stop‑loss automatically exits losing positions.

------------------------------------------------------------------------

# Warning

This bot is for **educational purposes**.\
Trading involves financial risk and real money can be lost.

Always test strategies thoroughly before running them in a live
environment.

------------------------------------------------------------------------

# Author

Trading Agent Project
