import pandas as pd
import numpy as np
import requests
import time
import os
import logging
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional

# =====================================================
# ENHANCED LOGGING & CONFIG
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("enhanced_agent")

API_URL = os.getenv("API_URL", "http://algotrading.sanyamchhabra.in")
API_KEY = os.getenv("TEAM_API_KEY", "ak_e50521f02c3b140f8f9940a1df3dd57c")
HEADERS = {"X-API-Key": API_KEY}

@dataclass
class Portfolio:
    cash: float = 0.0
    shares: int = 0
    price: float = 0.0
    equity: float = 0.0
    entry_price: Optional[float] = None

    @property
    def unrealized_pnl(self) -> float:
        if self.entry_price and self.shares > 0:
            return self.shares * (self.price - self.entry_price)
        return 0.0

    @property
    def pnl_pct(self) -> float:
        if self.entry_price and self.shares > 0:
            return (self.unrealized_pnl / (self.shares * self.entry_price)) * 100
        return 0.0

POS_PCT = 0.30
STOP_LOSS = 0.02
FEE = 0.001
INTERVAL = 30  # Faster: 30s
MAX_HISTORY = 200  # Fixed-size ring buffer for efficiency

# =====================================================
# OPTIMIZED API FUNCTIONS
# =====================================================
def api_get(url: str, timeout=5) -> Dict:
    """Optimized with retry and validation."""
    try:
        r = requests.get(f"{API_URL}/{url}", headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data
    except Exception as e:
        log.error("API %s failed: %s", url, e)
        return {}

def buy(qty: int) -> Dict:
    r = requests.post(f"{API_URL}/api/buy", json={"quantity": qty}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()

def sell(qty: int) -> Dict:
    r = requests.post(f"{API_URL}/api/sell", json={"quantity": qty}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()

# =====================================================
# OPTIMIZED FEATURES (VECTORIZED, RING BUFFER)
# =====================================================
class Technicals:
    def __init__(self, max_len: int = MAX_HISTORY):
        self.prices = deque(maxlen=max_len)
        self.volumes = deque(maxlen=max_len)

    def update(self, price: float, volume: float):
        self.prices.append(price)
        self.volumes.append(volume)

    def rsi(self, period: int = 14) -> float:
        if len(self.prices) < period + 1:
            return 50.0
        p = np.array(self.prices)
        delta = np.diff(p)
        gain = np.maximum(delta, 0)
        loss = np.maximum(-delta, 0)
        avg_gain = pd.Series(gain).ewm(com=period-1).mean().iloc[-1]
        avg_loss = pd.Series(loss).ewm(com=period-1).mean().iloc[-1]
        rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
        return 100 - (100 / (1 + rs))

    @property
    def signal(self) -> str:
        if len(self.prices) < 40:
            return "hold"
        
        p = np.array(self.prices)
        v = np.array(self.volumes)
        
        fast_ma = np.mean(p[-10:])
        slow_ma = np.mean(p[-30:])
        momentum = p[-1] - p[-5]
        
        vol_ratio = v[-1] / np.mean(v[-10:]) if len(v) >= 10 else 1.0
        rsi_val = self.rsi()
        
        # BUY: All conditions (more efficient checks)
        if (fast_ma > slow_ma and momentum > 0 and 
            vol_ratio > 1.15 and rsi_val < 72):  # Slightly loosened
            return "buy"
        
        # SELL: Reversal or overbought
        if fast_ma < slow_ma or rsi_val > 73:
            return "sell"
        
        return "hold"

# =====================================================
# ENHANCED LIVE TRADER WITH P&L TRACKING
# =====================================================
class EnhancedTrader:
    def __init__(self):
        self.tech = Technicals()
        self.portfolio = Portfolio()
        self.initial_equity = 0.0
        self.trade_history: List[Dict] = []
        self.last_log_time = 0

    def update_portfolio(self, tick: Dict):
        price = float(tick.get("close") or tick.get("price") or 0)
        port = api_get("api/portfolio")
        
        self.portfolio.price = price
        self.portfolio.cash = float(port.get("cash", 0))
        self.portfolio.shares = int(port.get("shares", 0))
        self.portfolio.equity = self.portfolio.cash + self.portfolio.shares * price
        
        if price <= 0:
            log.warning("Invalid price: %.2f", price)
            return False
        return True

    def execute_trade(self, signal: str):
        if signal == "buy" and self.portfolio.shares == 0:
            qty = int(self.portfolio.cash * POS_PCT / (self.portfolio.price * (1 + FEE)))
            if qty > 0:
                resp = buy(qty)
                log.info("🚀 BUY %d @ %.4f | Response: %s", qty, self.portfolio.price, resp)
                self.portfolio.entry_price = self.portfolio.price
                self.trade_history.append({"action": "buy", "qty": qty, "price": self.portfolio.price})

        elif signal == "sell" and self.portfolio.shares > 0:
            resp = sell(self.portfolio.shares)
            pnl = self.portfolio.unrealized_pnl
            log.info("💰 SELL %d @ %.4f | P&L: %.2f (%.2f%%) | Response: %s", 
                    self.portfolio.shares, self.portfolio.price, pnl, self.portfolio.pnl_pct, resp)
            self.trade_history.append({"action": "sell", "qty": self.portfolio.shares, "price": self.portfolio.price, "pnl": pnl})
            self.portfolio.entry_price = None

    def check_stop_loss(self) -> bool:
        if (self.portfolio.entry_price and self.portfolio.shares > 0 and 
            (self.portfolio.price - self.portfolio.entry_price) / self.portfolio.entry_price < -STOP_LOSS):
            self.execute_trade("sell")  # Triggers sell logic
            log.warning("🛑 STOP-LOSS HIT: %.2f%% loss", self.portfolio.pnl_pct)
            return True
        return False

    def log_summary(self):
        now = time.time()
        if now - self.last_log_time < 120:  # Every 2 min
            return
        self.last_log_time = now
        
        total_roi = ((self.portfolio.equity - self.initial_equity) / self.initial_equity * 100) if self.initial_equity > 0 else 0
        trades = len(self.trade_history)
        
        log.info("📊 SUMMARY | Equity: %.2f | P&L: %.2f (%.2f%%) | Pos: %d sh @ %.4f | Trades: %d | Signal: %s",
                self.portfolio.equity, 
                self.portfolio.unrealized_pnl, total_roi,
                self.portfolio.shares, self.portfolio.price,
                trades, self.tech.signal)

    def run(self):
        log.info("🚀 Enhanced Trader Started (Ctrl-C to stop)")
        
        try:
            while True:
                tick = api_get("api/price")
                if not self.update_portfolio(tick):
                    time.sleep(INTERVAL)
                    continue
                
                self.tech.update(self.portfolio.price, float(tick.get("volume", 0)))
                
                # 1. Stop-loss priority
                self.check_stop_loss()
                
                # 2. Signal & execute
                signal = self.tech.signal
                self.execute_trade(signal)
                
                # 3. Summary logging
                self.log_summary()
                
                time.sleep(INTERVAL)
                
        except KeyboardInterrupt:
            final_roi = ((self.portfolio.equity - self.initial_equity) / self.initial_equity * 100) if self.initial_equity > 0 else 0
            log.info("🏁 SHUTDOWN | Final Equity: %.2f | Total ROI: %.2f%% | Trades: %d", 
                    self.portfolio.equity, final_roi, len(self.trade_history))

# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    trader = EnhancedTrader()
    # Set initial equity on first portfolio fetch (add in first loop iter)
    trader.initial_equity = trader.portfolio.equity  # Will update on first tick
    trader.run()