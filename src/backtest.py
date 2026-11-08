"""Research-only EURUSD M3 VWAP/EMA9 backtester. No trading API or order execution."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

def prepare(m1: pd.DataFrame) -> pd.DataFrame:
    """M1 UTC OHLC + tick_volume -> completed 3-minute candles and indicators."""
    d = m1.copy()
    d["time"] = pd.to_datetime(d["time"], utc=True)
    d = d.sort_values("time").drop_duplicates("time").set_index("time")
    required = {"open", "high", "low", "close", "tick_volume"}
    if not required.issubset(d.columns):
        raise ValueError(f"Missing columns: {required - set(d.columns)}")
    if d.empty or (d["tick_volume"] < 0).any():
        raise ValueError("Empty or invalid input")
    # Do not aggregate across missing M1 bars.
    groups = d.resample("3min", origin="start_day", label="left", closed="left")
    bars = groups.agg({"open":"first","high":"max","low":"min","close":"last","tick_volume":"sum"})
    counts = groups["close"].count()
    bars = bars.loc[counts == 3].copy()
    bars["ema9"] = bars["close"].ewm(span=9, adjust=False).mean()
    bars["typical"] = (bars["high"] + bars["low"] + bars["close"]) / 3
    bars["pv"] = bars["typical"] * bars["tick_volume"]
    day = bars.index.floor("D")  # midnight UTC session reset
    volume = bars["tick_volume"].groupby(day).cumsum()
    bars["vwap"] = bars["pv"].groupby(day).cumsum() / volume.replace(0, np.nan)
    bars["cross_up"] = (bars["ema9"].shift(1) <= bars["vwap"].shift(1)) & (bars["ema9"] > bars["vwap"])
    bars["cross_down"] = (bars["ema9"].shift(1) >= bars["vwap"].shift(1)) & (bars["ema9"] < bars["vwap"])
    return bars

def simulate(bars: pd.DataFrame, initial_equity=1000.0, risk_fraction=.005,
             spread_pips=.8, slippage_pips=.2, commission_per_lot_side=3.5,
             min_lot=.01, lot_step=.01, max_stop_pips=30, swing_lookback=5,
             buffer_pips=1, daily_loss_fraction=.02):
    """Bid-based candles, approximate spread/slippage and conservative stop fills.

    Uses a fixed pip value of $10/standard lot (EURUSD in USD account).
    Entry at next M3 open; no same-bar exit signal; stop can trigger intrabar.
    """
    pip=.0001
    equity=float(initial_equity)
    trades=[]
    position=None
    day_start_equity=equity
    current_day=None
    for i in range(swing_lookback+1, len(bars)):
        now=bars.index[i]
        row=bars.iloc[i]
        previous=bars.iloc[i-1]
        day=now.date()
        if day != current_day:
            current_day=day
            day_start_equity=equity
        # Manage existing position first. Exit at current open after previous close signal.
        if position:
            side=position["side"]
            exit_price=None
            reason=None
            if (side==1 and previous["close"] < previous["ema9"]) or (side==-1 and previous["close"] > previous["ema9"]):
                exit_price=float(row["open"])+(spread_pips* pip if side==-1 else 0)
                exit_price-=side*slippage_pips*pip
                reason="ema_close"
            elif (side==1 and row["low"] <= position["stop"]) or (side==-1 and row["high"]+spread_pips*pip >= position["stop"]):
                exit_price=position["stop"]-side*slippage_pips*pip
                reason="stop"
            if exit_price is not None:
                gross=(exit_price-position["entry"])*side/pip*10*position["lots"]
                fees=2*commission_per_lot_side*position["lots"]
                pnl=gross-fees
                equity+=pnl
                trades.append({**position,"exit_time":str(now),"exit":exit_price,"reason":reason,"pnl":round(pnl,2),"equity":round(equity,2)})
                position=None
        if position or equity <= 0 or equity <= day_start_equity*(1-daily_loss_fraction):
            continue
        side=1 if previous["cross_up"] else -1 if previous["cross_down"] else 0
        if not side:
            continue
        lookback=bars.iloc[i-swing_lookback:i]
        entry=float(row["open"])+(spread_pips*pip if side==1 else 0)+side*slippage_pips*pip
        stop=(float(lookback["low"].min())-buffer_pips*pip if side==1
              else float(lookback["high"].max())+(buffer_pips+spread_pips)*pip)
        distance=(entry-stop)*side/pip
        if not 0 < distance <= max_stop_pips:
            continue
        # Reserve approximate round-trip commissions in the sizing budget.
        loss_per_lot=distance*10+2*commission_per_lot_side+slippage_pips*10
        lots=np.floor((equity*risk_fraction/loss_per_lot)/lot_step+1e-9)*lot_step
        if lots < min_lot:
            continue
        position={"entry_time":str(now),"entry":entry,"stop":stop,"side":side,"lots":round(float(lots),4)}
    # No imaginary closing fill: open positions remain marked as unclosed.
    pnls=np.array([t["pnl"] for t in trades], dtype=float)
    curve=np.r_[initial_equity,initial_equity+np.cumsum(pnls)]
    peak=np.maximum.accumulate(curve)
    drawdown=float(np.max((peak-curve)/peak)) if len(curve) else 0
    wins=pnls[pnls>0].sum()
    losses=-pnls[pnls<0].sum()
    return {"trades":trades,"open_position":position,"summary":{
        "trade_count":len(trades),"ending_equity":round(equity,2),
        "win_rate":float(np.mean(pnls>0)) if len(pnls) else None,
        "profit_factor":float(wins/losses) if losses else None,
        "expectancy_usd":float(np.mean(pnls)) if len(pnls) else None,
        "max_closed_trade_drawdown":drawdown}}

def main():
    parser=argparse.ArgumentParser(description="3M-VWAP offline research backtest; NEVER sends orders")
    parser.add_argument("csv", help="UTC M1 CSV: time,open,high,low,close,tick_volume")
    parser.add_argument("--output",default="results.json")
    args=parser.parse_args()
    bars=prepare(pd.read_csv(args.csv))
    result=simulate(bars)
    Path(args.output).write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")
    print(json.dumps(result["summary"],indent=2))
if __name__=="__main__":
    main()
