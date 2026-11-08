import pandas as pd
from src.backtest import prepare,simulate

def test_m3_aggregation_and_vwap_reset():
    t=pd.date_range("2026-01-01 23:57",periods=9,freq="min",tz="UTC")
    d=pd.DataFrame({"time":t,"open":[1.1]*9,"high":[1.2]*9,
        "low":[1.0]*9,"close":[1.1]*9,"tick_volume":[10]*9})
    b=prepare(d)
    assert len(b)==3
    assert b.iloc[0]["tick_volume"]==30
    assert abs(b.iloc[1]["vwap"]-1.1)<1e-10

def test_missing_minute_excluded():
    t=pd.date_range("2026-01-01",periods=6,freq="min",tz="UTC").delete(1)
    d=pd.DataFrame({"time":t,"open":1.1,"high":1.2,"low":1.0,"close":1.1,"tick_volume":10})
    assert len(prepare(d))==1

def test_no_trades_flat_market():
    t=pd.date_range("2026-01-01",periods=90,freq="min",tz="UTC")
    d=pd.DataFrame({"time":t,"open":1.1,"high":1.1,"low":1.1,"close":1.1,"tick_volume":10})
    assert simulate(prepare(d))["summary"]["trade_count"]==0
