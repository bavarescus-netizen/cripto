"""
scanner.py - Scanner de Mercado
Corre todas las estrategias sobre todos los pares y genera señales
"""

import asyncio
from binance.client import Client
from src.binance_client import binance, MAJOR_PAIRS, MEME_PAIRS
from src.strategies import (
    strategy_scalp_rsi_bb,
    strategy_scalp_macd,
    strategy_swing_trend,
    strategy_meme_breakout,
    save_signal,
    TradeSignal
)
from src.database import get_config


def scan_scalping(pairs: list[str]) -> list[TradeSignal]:
    """Escanear pares con estrategias de scalping (1m y 5m)"""
    signals = []

    for symbol in pairs:
        try:
            # Estrategia 1: RSI + BB en 1m
            candles_1m = binance.get_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, limit=80)
            sig = strategy_scalp_rsi_bb(symbol, candles_1m)
            if sig:
                save_signal(sig)
                signals.append(sig)
                continue  # Una señal por par

            # Estrategia 2: MACD Cross en 5m
            candles_5m = binance.get_klines(symbol, Client.KLINE_INTERVAL_5MINUTE, limit=80)
            sig = strategy_scalp_macd(symbol, candles_5m)
            if sig:
                save_signal(sig)
                signals.append(sig)

        except Exception as e:
            print(f"⚠️ Error escaneando {symbol}: {e}")

    return signals


def scan_swing(pairs: list[str]) -> list[TradeSignal]:
    """Escanear pares con estrategia swing (1h + 4h)"""
    signals = []

    for symbol in pairs:
        try:
            candles_1h = binance.get_klines(symbol, Client.KLINE_INTERVAL_1HOUR, limit=100)
            candles_4h = binance.get_klines(symbol, Client.KLINE_INTERVAL_4HOUR, limit=100)
            sig = strategy_swing_trend(symbol, candles_1h, candles_4h)
            if sig:
                save_signal(sig)
                signals.append(sig)
        except Exception as e:
            print(f"⚠️ Error swing {symbol}: {e}")

    return signals


def scan_memes(pairs: list[str]) -> list[TradeSignal]:
    """Escanear meme coins buscando breakouts explosivos"""
    signals = []

    # También buscar nuevos movers dinámicos
    top_movers = binance.get_top_movers(limit=20)
    dynamic_memes = [
        t["symbol"] for t in top_movers
        if abs(float(t["priceChangePercent"])) > 8
        and t["symbol"] not in pairs
        and t["symbol"].endswith("USDT")
    ]

    all_meme_pairs = list(set(pairs + dynamic_memes))

    for symbol in all_meme_pairs:
        try:
            candles_5m = binance.get_klines(symbol, Client.KLINE_INTERVAL_5MINUTE, limit=50)
            stats_24h  = binance.get_24h_stats(symbol)
            sig = strategy_meme_breakout(symbol, candles_5m, stats_24h)
            if sig:
                save_signal(sig)
                signals.append(sig)
        except Exception as e:
            print(f"⚠️ Error meme scan {symbol}: {e}")

    return signals


def run_full_scan() -> dict:
    """
    Escaneo completo del mercado.
    Retorna dict con señales organizadas por tipo.
    """
    scalp_pairs  = get_config("active_pairs", "BTCUSDT,ETHUSDT,SOLUSDT").split(",")
    meme_pairs   = get_config("meme_pairs",   "DOGEUSDT,PEPEUSDT,SHIBUSDT,BONKUSDT").split(",")

    scalp_on = get_config("scalp_enabled", "true").lower() == "true"
    swing_on  = get_config("swing_enabled", "true").lower() == "true"
    meme_on   = get_config("meme_enabled",  "true").lower() == "true"

    results = {"scalp": [], "swing": [], "meme": [], "total": 0}

    if scalp_on:
        results["scalp"] = scan_scalping(scalp_pairs)

    if swing_on:
        results["swing"] = scan_swing(scalp_pairs)

    if meme_on:
        results["meme"] = scan_memes(meme_pairs)

    results["total"] = len(results["scalp"]) + len(results["swing"]) + len(results["meme"])
    return results


def get_market_overview() -> str:
    """Resumen rápido del mercado para el menú de Telegram"""
    lines = ["📡 *ESTADO DEL MERCADO*\n━━━━━━━━━━━━━━━━━━━━━━"]

    pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "PEPEUSDT"]
    for symbol in pairs:
        try:
            stats = binance.get_24h_stats(symbol)
            chg   = stats.get("price_change_pct", 0)
            price = stats.get("last_price", 0)
            arrow = "🟢" if chg >= 0 else "🔴"
            lines.append(f"{arrow} `{symbol}` — ${price:,.4f} ({chg:+.2f}%)")
        except Exception:
            lines.append(f"⚠️ `{symbol}` — Sin datos")

    # Top mover del momento
    try:
        movers = binance.get_top_movers(limit=3)
        if movers:
            lines.append("\n🔥 *TOP MOVERS 24H*")
            for m in movers[:3]:
                chg = float(m["priceChangePercent"])
                lines.append(f"{'🚀' if chg > 0 else '💥'} `{m['symbol']}` {chg:+.1f}%")
    except Exception:
        pass

    return "\n".join(lines)
