"""
strategies.py - Motor de Estrategias con Aprendizaje
Scalping (1m, 5m) + Swing (1h, 4h) + Detección de Memes calientes
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice

from src.database import get_config, MarketSignal, SessionLocal


# ─── SEÑAL DE TRADING ────────────────────────────────────────────────────────

@dataclass
class TradeSignal:
    symbol:       str
    direction:    str          # LONG | SHORT
    strategy:     str          # scalp_rsi | scalp_macd | swing_trend | meme_breakout
    timeframe:    str          # 1m | 5m | 1h | 4h
    entry_price:  float
    take_profit:  float
    stop_loss:    float
    strength:     float        # 0-100 (confianza de la señal)
    indicators:   dict         # Snapshot para aprendizaje
    reason:       str          # Descripción humana


# ─── UTILIDADES ──────────────────────────────────────────────────────────────

def candles_to_df(candles: list) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(candles)
    df["close"]  = df["close"].astype(float)
    df["high"]   = df["high"].astype(float)
    df["low"]    = df["low"].astype(float)
    df["open"]   = df["open"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df


def compute_indicators(df: pd.DataFrame) -> dict:
    """Calcular todos los indicadores técnicos"""
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    # RSI
    rsi = RSIIndicator(close, window=14).rsi()

    # MACD
    macd_obj = MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd_obj.macd()
    macd_signal = macd_obj.macd_signal()
    macd_hist = macd_obj.macd_diff()

    # EMAs
    ema9  = EMAIndicator(close, window=9).ema_indicator()
    ema21 = EMAIndicator(close, window=21).ema_indicator()
    ema50 = EMAIndicator(close, window=50).ema_indicator()
    ema200 = EMAIndicator(close, window=200).ema_indicator() if len(df) >= 200 else ema50

    # Bollinger Bands
    bb = BollingerBands(close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband()
    bb_lower = bb.bollinger_lband()
    bb_mid   = bb.bollinger_mavg()
    bb_width = ((bb_upper - bb_lower) / bb_mid * 100)

    # ADX (fuerza de tendencia)
    adx_obj = ADXIndicator(high, low, close, window=14)
    adx = adx_obj.adx()

    # Stochastic
    stoch = StochasticOscillator(high, low, close, window=14, smooth_window=3)
    stoch_k = stoch.stoch()
    stoch_d = stoch.stoch_signal()

    # ATR (volatilidad)
    atr = AverageTrueRange(high, low, close, window=14).average_true_range()

    # Volume MA
    vol_ma20 = vol.rolling(20).mean()

    # Retornar últimos valores
    i = -1
    return {
        "rsi":         round(float(rsi.iloc[i]), 2),
        "macd":        round(float(macd_line.iloc[i]), 6),
        "macd_signal": round(float(macd_signal.iloc[i]), 6),
        "macd_hist":   round(float(macd_hist.iloc[i]), 6),
        "macd_hist_prev": round(float(macd_hist.iloc[-2]), 6),
        "ema9":        round(float(ema9.iloc[i]), 6),
        "ema21":       round(float(ema21.iloc[i]), 6),
        "ema50":       round(float(ema50.iloc[i]), 6),
        "ema200":      round(float(ema200.iloc[i]), 6),
        "bb_upper":    round(float(bb_upper.iloc[i]), 6),
        "bb_lower":    round(float(bb_lower.iloc[i]), 6),
        "bb_mid":      round(float(bb_mid.iloc[i]), 6),
        "bb_width":    round(float(bb_width.iloc[i]), 2),
        "adx":         round(float(adx.iloc[i]), 2),
        "stoch_k":     round(float(stoch_k.iloc[i]), 2),
        "stoch_d":     round(float(stoch_d.iloc[i]), 2),
        "atr":         round(float(atr.iloc[i]), 6),
        "volume":      round(float(vol.iloc[i]), 2),
        "vol_ma20":    round(float(vol_ma20.iloc[i]), 2),
        "close":       round(float(df["close"].iloc[i]), 6),
        "high":        round(float(df["high"].iloc[i]), 6),
        "low":         round(float(df["low"].iloc[i]), 6),
    }


# ─── ESTRATEGIA 1: SCALPING RSI + BB (1min / 5min) ──────────────────────────

def strategy_scalp_rsi_bb(symbol: str, candles: list) -> Optional[TradeSignal]:
    """
    Scalping rápido en 1m/5m:
    - RSI en zona extrema (< 30 oversold, > 70 overbought)
    - Precio tocando bandas de Bollinger
    - MACD confirmando dirección
    - Volumen por encima de la media
    """
    df = candles_to_df(candles)
    if len(df) < 30:
        return None

    ind = compute_indicators(df)
    price = ind["close"]
    strength = 0.0
    direction = None
    reason_parts = []

    # ── LONG ──
    long_conditions = [
        ind["rsi"] < 32,
        price < ind["bb_lower"] * 1.002,
        ind["macd_hist"] > ind["macd_hist_prev"],     # MACD histograma creciendo
        ind["stoch_k"] < 25,
        ind["volume"] > ind["vol_ma20"] * 1.3,        # Volumen elevado
    ]
    long_score = sum(long_conditions)

    # ── SHORT ──
    short_conditions = [
        ind["rsi"] > 68,
        price > ind["bb_upper"] * 0.998,
        ind["macd_hist"] < ind["macd_hist_prev"],     # MACD cayendo
        ind["stoch_k"] > 75,
        ind["volume"] > ind["vol_ma20"] * 1.3,
    ]
    short_score = sum(short_conditions)

    if long_score >= 3:
        direction = "LONG"
        strength  = (long_score / 5) * 100
        reason_parts = [
            f"RSI={ind['rsi']} (oversold)" if ind["rsi"] < 32 else "",
            f"Precio en BB inferior" if price < ind["bb_lower"] * 1.002 else "",
            f"MACD divergencia alcista" if ind["macd_hist"] > ind["macd_hist_prev"] else "",
        ]
    elif short_score >= 3:
        direction = "SHORT"
        strength  = (short_score / 5) * 100
        reason_parts = [
            f"RSI={ind['rsi']} (overbought)" if ind["rsi"] > 68 else "",
            f"Precio en BB superior" if price > ind["bb_upper"] * 0.998 else "",
            f"MACD divergencia bajista" if ind["macd_hist"] < ind["macd_hist_prev"] else "",
        ]

    if not direction:
        return None

    # TP/SL dinámico basado en ATR
    atr = ind["atr"]
    tp_mult = float(get_config("scalp_tp_pct", "0.8")) / 100
    sl_mult = float(get_config("scalp_sl_pct", "0.4")) / 100

    if direction == "LONG":
        tp = price * (1 + tp_mult)
        sl = price * (1 - sl_mult)
    else:
        tp = price * (1 - tp_mult)
        sl = price * (1 + sl_mult)

    return TradeSignal(
        symbol=symbol,
        direction=direction,
        strategy="scalp_rsi_bb",
        timeframe="1m",
        entry_price=price,
        take_profit=round(tp, 6),
        stop_loss=round(sl, 6),
        strength=round(strength, 1),
        indicators=ind,
        reason=" | ".join(r for r in reason_parts if r)
    )


# ─── ESTRATEGIA 2: SCALPING MACD CROSS (5min) ────────────────────────────────

def strategy_scalp_macd(symbol: str, candles: list) -> Optional[TradeSignal]:
    """
    Cruce de MACD con confirmación de EMA y volumen
    """
    df = candles_to_df(candles)
    if len(df) < 50:
        return None

    ind = compute_indicators(df)
    price = ind["close"]

    # Cruce MACD: histograma cambia de signo
    hist_now  = ind["macd_hist"]
    hist_prev = ind["macd_hist_prev"]
    
    cross_up   = hist_now > 0 and hist_prev <= 0
    cross_down = hist_now < 0 and hist_prev >= 0

    if not (cross_up or cross_down):
        return None

    # Confirmar con EMA trend
    ema_bullish = ind["ema9"] > ind["ema21"] > ind["ema50"]
    ema_bearish = ind["ema9"] < ind["ema21"] < ind["ema50"]

    # ADX debe indicar tendencia
    if ind["adx"] < 20:
        return None

    direction = None
    strength  = 0.0

    if cross_up and (ema_bullish or ind["ema9"] > ind["ema21"]):
        direction = "LONG"
        strength  = min(90, 50 + ind["adx"])
    elif cross_down and (ema_bearish or ind["ema9"] < ind["ema21"]):
        direction = "SHORT"
        strength  = min(90, 50 + ind["adx"])

    if not direction:
        return None

    tp_pct = float(get_config("scalp_tp_pct", "0.8")) / 100
    sl_pct = float(get_config("scalp_sl_pct", "0.4")) / 100

    tp = price * (1 + tp_pct) if direction == "LONG" else price * (1 - tp_pct)
    sl = price * (1 - sl_pct) if direction == "LONG" else price * (1 + sl_pct)

    return TradeSignal(
        symbol=symbol,
        direction=direction,
        strategy="scalp_macd_cross",
        timeframe="5m",
        entry_price=price,
        take_profit=round(tp, 6),
        stop_loss=round(sl, 6),
        strength=round(strength, 1),
        indicators=ind,
        reason=f"Cruce MACD {'alcista' if direction == 'LONG' else 'bajista'} | ADX={ind['adx']} | EMA trend {'OK' if (ema_bullish if direction == 'LONG' else ema_bearish) else 'parcial'}"
    )


# ─── ESTRATEGIA 3: SWING TRADING (1h / 4h) ───────────────────────────────────

def strategy_swing_trend(symbol: str, candles_1h: list, candles_4h: list) -> Optional[TradeSignal]:
    """
    Swing de mayor duración:
    - Tendencia en 4h (EMA 50/200)
    - Entrada en pullback en 1h
    - RSI no extremo (zona 40-60)
    """
    df1h = candles_to_df(candles_1h)
    df4h = candles_to_df(candles_4h)

    if len(df1h) < 50 or len(df4h) < 50:
        return None

    ind1h = compute_indicators(df1h)
    ind4h = compute_indicators(df4h)
    price = ind1h["close"]

    # Tendencia macro en 4h
    trend_up   = ind4h["ema50"] > ind4h["ema200"] and ind4h["adx"] > 25
    trend_down = ind4h["ema50"] < ind4h["ema200"] and ind4h["adx"] > 25

    if not (trend_up or trend_down):
        return None

    direction = None
    reason    = ""

    # Pullback en 1h con RSI no extremo
    if trend_up:
        pullback_long = (
            ind1h["rsi"] > 35 and ind1h["rsi"] < 60 and
            price > ind1h["ema21"] and
            ind1h["macd_hist"] > 0
        )
        if pullback_long:
            direction = "LONG"
            reason = f"Tendencia 4h alcista | Pullback 1h | RSI={ind1h['rsi']}"

    elif trend_down:
        pullback_short = (
            ind1h["rsi"] < 65 and ind1h["rsi"] > 40 and
            price < ind1h["ema21"] and
            ind1h["macd_hist"] < 0
        )
        if pullback_short:
            direction = "SHORT"
            reason = f"Tendencia 4h bajista | Pullback 1h | RSI={ind1h['rsi']}"

    if not direction:
        return None

    tp_pct = float(get_config("swing_tp_pct", "3.0")) / 100
    sl_pct = float(get_config("swing_sl_pct", "1.5")) / 100

    tp = price * (1 + tp_pct) if direction == "LONG" else price * (1 - tp_pct)
    sl = price * (1 - sl_pct) if direction == "LONG" else price * (1 + sl_pct)

    return TradeSignal(
        symbol=symbol,
        direction=direction,
        strategy="swing_trend",
        timeframe="1h",
        entry_price=price,
        take_profit=round(tp, 6),
        stop_loss=round(sl, 6),
        strength=round(min(95, 60 + ind4h["adx"]), 1),
        indicators={"1h": ind1h, "4h": ind4h},
        reason=reason
    )


# ─── ESTRATEGIA 4: MEME COINS BREAKOUT ───────────────────────────────────────

def strategy_meme_breakout(symbol: str, candles: list, stats_24h: dict) -> Optional[TradeSignal]:
    """
    Detecta breakouts en meme coins:
    - Cambio de precio > 5% en 24h
    - Volumen 3x por encima de la media
    - RSI entre 50-70 (momentum sin sobrecompra extrema)
    - Precio rompiendo BB superior
    """
    df = candles_to_df(candles)
    if len(df) < 20:
        return None

    ind   = compute_indicators(df)
    price = ind["close"]

    price_change = abs(stats_24h.get("price_change_pct", 0))
    volume_usdt  = stats_24h.get("volume_usdt", 0)

    if price_change < 5:        # Al menos 5% de movimiento
        return None
    if volume_usdt < 500_000:   # Al menos 500k USDT en volumen
        return None
    if ind["volume"] < ind["vol_ma20"] * 2:  # Volumen actual 2x la media
        return None

    direction = "LONG" if stats_24h.get("price_change_pct", 0) > 0 else "SHORT"

    # Para LONG: RSI no debe estar ya sobrecomprado extremo
    if direction == "LONG" and ind["rsi"] > 80:
        return None
    if direction == "SHORT" and ind["rsi"] < 20:
        return None

    strength = min(95, 40 + price_change * 3 + (ind["volume"] / ind["vol_ma20"]) * 5)

    tp_pct = 0.05   # 5% TP para memes (más volátiles)
    sl_pct = 0.025  # 2.5% SL

    tp = price * (1 + tp_pct) if direction == "LONG" else price * (1 - tp_pct)
    sl = price * (1 - sl_pct) if direction == "LONG" else price * (1 + sl_pct)

    return TradeSignal(
        symbol=symbol,
        direction=direction,
        strategy="meme_breakout",
        timeframe="5m",
        entry_price=price,
        take_profit=round(tp, 6),
        stop_loss=round(sl, 6),
        strength=round(strength, 1),
        indicators=ind,
        reason=f"🚀 MEME BREAKOUT | {price_change:.1f}% en 24h | Vol={volume_usdt/1_000_000:.1f}M USDT | RSI={ind['rsi']}"
    )


# ─── MOTOR DE SEÑALES ─────────────────────────────────────────────────────────

def save_signal(signal: TradeSignal):
    """Guardar señal en DB para aprendizaje"""
    with SessionLocal() as db:
        ms = MarketSignal(
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            signal_type=signal.strategy,
            direction=signal.direction,
            strength=signal.strength,
            price_at_signal=signal.entry_price,
            indicators=signal.indicators,
        )
        db.add(ms)
        db.commit()


def format_signal_message(signal: TradeSignal) -> str:
    """Formatear señal para Telegram"""
    emoji = "🟢" if signal.direction == "LONG" else "🔴"
    strat_emojis = {
        "scalp_rsi_bb":    "⚡",
        "scalp_macd_cross": "📊",
        "swing_trend":     "📈",
        "meme_breakout":   "🚀",
    }
    e = strat_emojis.get(signal.strategy, "💡")

    return (
        f"{emoji} *SEÑAL {signal.direction}* {e}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 Par: `{signal.symbol}`\n"
        f"⏱ Timeframe: `{signal.timeframe}`\n"
        f"📋 Estrategia: `{signal.strategy}`\n"
        f"💰 Entrada: `{signal.entry_price}`\n"
        f"🎯 Take Profit: `{signal.take_profit}`\n"
        f"🛡 Stop Loss: `{signal.stop_loss}`\n"
        f"💪 Fuerza: `{signal.strength}%`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 {signal.reason}"
    )
