"""Read-only MT5 M1 history export. Windows terminal required; no order methods."""
import argparse
from datetime import datetime, timezone
import pandas as pd

def export(symbol, start, end, output):
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        rates=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,start,end)
        if rates is None or len(rates)==0:
            raise RuntimeError(f"No MT5 history: {mt5.last_error()}")
        frame=pd.DataFrame(rates)
        frame["time"]=pd.to_datetime(frame["time"],unit="s",utc=True)
        frame[["time","open","high","low","close","tick_volume"]].to_csv(output,index=False)
        print(f"Exported {len(frame)} M1 bars to {output}")
    finally:
        mt5.shutdown()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",default="EURUSD")
    p.add_argument("--start",required=True,help="UTC YYYY-MM-DD")
    p.add_argument("--end",required=True,help="UTC YYYY-MM-DD")
    p.add_argument("--output",default="eurusd_m1.csv")
    a=p.parse_args()
    export(a.symbol,datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc),
           datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc),a.output)
