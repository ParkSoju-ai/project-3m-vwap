# Project 3M-VWAP

Research-only EUR/USD M3 VWAP + EMA9 crossover backtester. **No live trading or order submission.**

## Install and test

```bash
pip install -r requirements.txt
python -m pytest -q
```

On Windows with MT5 installed, export read-only historical M1 data:

```bash
python -m src.mt5_export --symbol EURUSD --start 2025-01-01 --end 2026-01-01 --output eurusd_m1.csv
python -m src.backtest eurusd_m1.csv --output results.json
```

## Research assumptions

- Complete UTC M1 bars aggregate to M3. Daily VWAP resets at 00:00 UTC using broker tick volume, not exchange volume.
- EMA9/VWAP cross is confirmed on the completed candle. Enter at the next candle open.
- Protective swing stop and EMA9 close exit. One position at a time; default 0.5% equity risk and 2% daily realized-loss entry lock.
- Approximate fixed spread, slippage and commission; fixed $10/pip/standard lot for USD-account EURUSD.
- Reject trades if minimum lot exceeds risk budget. No martingale.

## Known limitations — do not use for live trading

This is an initial research prototype, not a validated strategy. Fixed spread and M3 OHLC cannot reproduce tick-level stop execution; when an EMA exit and stop are possible in the same bar, exit ordering is approximate. Daily loss lock ignores floating loss. No broker-specific symbol constraints, gap modeling or mark-to-market for an open final trade. Run 12+ months, out-of-sample tests and sensitivity analysis after improving fill simulation. The bot cannot place orders.
