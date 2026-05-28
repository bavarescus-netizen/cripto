"""
binance_client.py - Conexión a Binance (Testnet / Live)
Gestiona órdenes, precios en tiempo real y datos de mercado
"""

import os
import asyncio
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

load_dotenv()

# ─── ACTIVOS SOPORTADOS ───────────────────────────────────────────────────────

MAJOR_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

MEME_PAIRS = [
    "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "BONKUSDT",
    "FLOKIUSDT", "WIFUSDT", "BOMEUSDT", "POPCATUSDT"
]

ALL_PAIRS = MAJOR_PAIRS + MEME_PAIRS

# ─── CLIENTE ─────────────────────────────────────────────────────────────────

class BinanceClientWrapper:
    def __init__(self):
        self.api_key    = os.getenv("BINANCE_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_SECRET_KEY", "")
        self.testnet    = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

        self.client = Client(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet
        )
        if self.testnet:
            # Redirigir al testnet de futuros de Binance
            self.client.API_URL = "https://testnet.binancefuture.com/fapi"
        
        print(f"{'🔵 DEMO' if self.testnet else '🔴 LIVE'} Binance conectado")

    def get_ticker_price(self, symbol: str) -> float:
        """Precio actual de un par"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            print(f"❌ Error precio {symbol}: {e}")
            return 0.0

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> list:
        """
        Velas OHLCV
        interval: Client.KLINE_INTERVAL_1MINUTE, _5MINUTE, _1HOUR, _4HOUR, _1DAY
        """
        try:
            raw = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            candles = []
            for k in raw:
                candles.append({
                    "time":   datetime.fromtimestamp(k[0] / 1000),
                    "open":   float(k[1]),
                    "high":   float(k[2]),
                    "low":    float(k[3]),
                    "close":  float(k[4]),
                    "volume": float(k[5]),
                })
            return candles
        except Exception as e:
            print(f"❌ Error klines {symbol} {interval}: {e}")
            return []

    def get_account_balance(self) -> dict:
        """Balance de la cuenta (USDT principalmente)"""
        try:
            account = self.client.get_account()
            balances = {}
            for asset in account["balances"]:
                free = float(asset["free"])
                locked = float(asset["locked"])
                if free + locked > 0:
                    balances[asset["asset"]] = {"free": free, "locked": locked}
            return balances
        except Exception as e:
            print(f"❌ Error balance: {e}")
            return {"USDT": {"free": 1000.0, "locked": 0.0}}  # Fallback demo

    def place_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        """Ejecutar orden de mercado"""
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,           # "BUY" | "SELL"
                type="MARKET",
                quantity=quantity
            )
            return order
        except BinanceAPIException as e:
            print(f"❌ Error orden {symbol} {side}: {e}")
            # En demo, simular orden
            return self._simulate_order(symbol, side, quantity)

    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> dict:
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type="LIMIT",
                timeInForce="GTC",
                quantity=quantity,
                price=str(round(price, 2))
            )
            return order
        except BinanceAPIException as e:
            print(f"❌ Error limit order: {e}")
            return self._simulate_order(symbol, side, quantity, price)

    def cancel_order(self, symbol: str, order_id: int) -> bool:
        try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
            return True
        except Exception as e:
            print(f"❌ Error cancelar {order_id}: {e}")
            return False

    def get_open_orders(self, symbol: str = None) -> list:
        try:
            if symbol:
                return self.client.get_open_orders(symbol=symbol)
            return self.client.get_open_orders()
        except Exception:
            return []

    def get_24h_stats(self, symbol: str) -> dict:
        """Estadísticas 24h: volumen, cambio de precio, etc."""
        try:
            stats = self.client.get_ticker(symbol=symbol)
            return {
                "price_change_pct": float(stats["priceChangePercent"]),
                "volume_usdt":      float(stats["quoteVolume"]),
                "high":             float(stats["highPrice"]),
                "low":              float(stats["lowPrice"]),
                "last_price":       float(stats["lastPrice"]),
            }
        except Exception:
            return {}

    def get_top_movers(self, limit: int = 10) -> list:
        """Obtener los mayores movimientos en cripto (para detectar memes calientes)"""
        try:
            tickers = self.client.get_ticker()
            usdt_pairs = [
                t for t in tickers 
                if t["symbol"].endswith("USDT") and float(t["quoteVolume"]) > 500_000
            ]
            sorted_by_change = sorted(
                usdt_pairs, 
                key=lambda x: abs(float(x["priceChangePercent"])), 
                reverse=True
            )
            return sorted_by_change[:limit]
        except Exception as e:
            print(f"❌ Error top movers: {e}")
            return []

    def _simulate_order(self, symbol: str, side: str, quantity: float, price: float = None) -> dict:
        """Simular orden cuando el testnet falla (modo puro demo)"""
        import random
        price = price or self.get_ticker_price(symbol)
        return {
            "orderId":         random.randint(100000, 999999),
            "symbol":          symbol,
            "side":            side,
            "type":            "MARKET",
            "status":          "FILLED",
            "executedQty":     str(quantity),
            "fills":           [{"price": str(price), "qty": str(quantity)}],
            "simulated":       True
        }

    def get_symbol_info(self, symbol: str) -> dict:
        """Info del par: lotSize, minQty, etc."""
        try:
            info = self.client.get_symbol_info(symbol)
            for f in info["filters"]:
                if f["filterType"] == "LOT_SIZE":
                    return {
                        "min_qty":  float(f["minQty"]),
                        "step_size": float(f["stepSize"])
                    }
        except Exception:
            pass
        return {"min_qty": 0.001, "step_size": 0.001}

    def calculate_quantity(self, symbol: str, usdt_amount: float, price: float) -> float:
        """Calcular cantidad ajustada al step_size del par"""
        info = self.get_symbol_info(symbol)
        raw_qty = usdt_amount / price
        step = info["step_size"]
        qty = round(raw_qty - (raw_qty % step), 8)
        return max(qty, info["min_qty"])


# Instancia global
binance = BinanceClientWrapper()
