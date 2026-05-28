"""
executor.py - Ejecutor de Operaciones con Gestión de Riesgo
Maneja apertura/cierre de trades, interés compuesto y risk management
"""

import os
from datetime import datetime
from src.database import (
    Trade, PortfolioSnapshot, LearningStats,
    SessionLocal, get_config, set_config, get_open_trades
)
from src.binance_client import binance
from src.strategies import TradeSignal


def get_usdt_balance() -> float:
    """Balance USDT disponible"""
    balances = binance.get_account_balance()
    return balances.get("USDT", {}).get("free", 0.0)


def calculate_position_size(price: float) -> float:
    """
    Calcular tamaño de posición con gestión de riesgo:
    - Máximo X% del capital por trade
    - Interés compuesto: reinvertir % de ganancias
    """
    balance      = get_usdt_balance()
    risk_pct     = float(get_config("max_risk_per_trade", "2")) / 100
    max_trades   = int(get_config("max_open_trades", "3"))
    open_trades  = len(get_open_trades())

    if open_trades >= max_trades:
        return 0.0

    # Distribuir capital disponible entre slots restantes
    slots_left   = max_trades - open_trades
    per_slot_usdt = balance / max_trades
    position_usdt = per_slot_usdt * risk_pct * 10  # Kelly fracción

    # Mínimo 10 USDT, máximo 30% del balance
    position_usdt = max(10.0, min(position_usdt, balance * 0.30))
    return round(position_usdt, 2)


def open_trade(signal: TradeSignal, notify_fn=None) -> Trade | None:
    """
    Abrir operación a partir de una señal
    """
    position_usdt = calculate_position_size(signal.entry_price)
    if position_usdt <= 0:
        return None

    quantity = binance.calculate_quantity(signal.symbol, position_usdt, signal.entry_price)
    if quantity <= 0:
        return None

    # Ejecutar orden
    side  = "BUY" if signal.direction == "LONG" else "SELL"
    order = binance.place_market_order(signal.symbol, side, quantity)

    if not order or order.get("status") not in ("FILLED", "PARTIALLY_FILLED"):
        print(f"❌ Orden no ejecutada para {signal.symbol}")
        return None

    # Precio real de ejecución
    fills = order.get("fills", [])
    if fills:
        exec_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / sum(float(f["qty"]) for f in fills)
    else:
        exec_price = signal.entry_price

    with SessionLocal() as db:
        trade = Trade(
            order_id    = order["orderId"],
            symbol      = signal.symbol,
            side        = side,
            strategy    = signal.strategy,
            timeframe   = signal.timeframe,
            entry_price = exec_price,
            quantity    = quantity,
            take_profit = signal.take_profit,
            stop_loss   = signal.stop_loss,
            status      = "OPEN",
            signal_data = signal.indicators,
            is_demo     = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade


def check_and_close_trades(notify_fn=None):
    """
    Revisar todas las operaciones abiertas y cerrar si alcanzan TP/SL
    Llamar cada minuto desde el scheduler
    """
    open_trades = get_open_trades()
    if not open_trades:
        return

    with SessionLocal() as db:
        for trade in open_trades:
            price = binance.get_ticker_price(trade.symbol)
            if price <= 0:
                continue

            should_close = False
            close_reason = ""

            if trade.side == "BUY":  # LONG
                if price >= trade.take_profit:
                    should_close = True
                    close_reason = "✅ TAKE PROFIT"
                elif price <= trade.stop_loss:
                    should_close = True
                    close_reason = "🛑 STOP LOSS"

            else:  # SHORT
                if price <= trade.take_profit:
                    should_close = True
                    close_reason = "✅ TAKE PROFIT"
                elif price >= trade.stop_loss:
                    should_close = True
                    close_reason = "🛑 STOP LOSS"

            if should_close:
                _close_trade(db, trade, price, close_reason, notify_fn)


def _close_trade(db, trade, exit_price: float, reason: str, notify_fn=None):
    """Cerrar una operación y calcular PnL"""
    # Ejecutar orden de cierre
    close_side = "SELL" if trade.side == "BUY" else "BUY"
    binance.place_market_order(trade.symbol, close_side, trade.quantity)

    # Calcular PnL
    if trade.side == "BUY":
        pnl = (exit_price - trade.entry_price) * trade.quantity
    else:
        pnl = (trade.entry_price - exit_price) * trade.quantity

    pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100

    # Actualizar trade en DB
    t = db.query(Trade).filter(Trade.id == trade.id).first()
    t.exit_price = exit_price
    t.pnl        = round(pnl, 4)
    t.pnl_pct    = round(pnl_pct, 2)
    t.status     = "CLOSED"
    t.closed_at  = datetime.utcnow()
    db.commit()

    # Interés compuesto: reinvertir % de ganancias
    if pnl > 0:
        _apply_compound_interest(pnl)

    # Actualizar estadísticas de aprendizaje
    _update_learning_stats(trade, pnl > 0, pnl)

    # Notificar por Telegram
    if notify_fn:
        emoji = "✅" if pnl > 0 else "❌"
        msg = (
            f"{emoji} *OPERACIÓN CERRADA*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Par: `{trade.symbol}`\n"
            f"📋 Razón: {reason}\n"
            f"💰 Entrada: `{trade.entry_price}`\n"
            f"🏁 Salida: `{exit_price}`\n"
            f"{'🟢' if pnl > 0 else '🔴'} PnL: `{'+' if pnl > 0 else ''}{pnl:.4f} USDT ({pnl_pct:+.2f}%)`\n"
            f"📊 Estrategia: `{trade.strategy}`"
        )
        try:
            notify_fn(msg)
        except Exception:
            pass

    print(f"{'✅' if pnl > 0 else '❌'} Cerrado {trade.symbol} | PnL: {pnl:+.4f} USDT")


def _apply_compound_interest(profit_usdt: float):
    """Registrar ganancia para el cálculo de interés compuesto"""
    reinvest_pct = float(get_config("compound_reinvest", "80")) / 100
    reinvest_amt = profit_usdt * reinvest_pct
    # El reinvestimiento es automático al mantener el balance en Binance
    # Aquí guardamos snapshot del capital para tracking
    balance = get_usdt_balance()
    with SessionLocal() as db:
        snap = PortfolioSnapshot(
            balance=balance,
            open_pnl=0.0,
            total_value=balance
        )
        db.add(snap)
        db.commit()


def _update_learning_stats(trade, is_win: bool, pnl: float):
    """Actualizar estadísticas de aprendizaje por estrategia"""
    with SessionLocal() as db:
        stats = db.query(LearningStats).filter(
            LearningStats.symbol   == trade.symbol,
            LearningStats.strategy == trade.strategy,
            LearningStats.timeframe == trade.timeframe
        ).first()

        if not stats:
            stats = LearningStats(
                symbol=trade.symbol,
                strategy=trade.strategy,
                timeframe=trade.timeframe
            )
            db.add(stats)

        stats.total_trades   += 1
        stats.total_pnl      += pnl
        if is_win:
            stats.winning_trades += 1
            stats.avg_win = stats.total_pnl / max(stats.winning_trades, 1)
        else:
            losses = stats.total_trades - stats.winning_trades
            stats.avg_loss = abs(pnl) / max(losses, 1)
        stats.updated_at = datetime.utcnow()
        db.commit()


def get_portfolio_summary() -> dict:
    """Resumen del portafolio para mostrar en Telegram"""
    balance    = get_usdt_balance()
    initial    = float(get_config("initial_capital", "1000"))
    open_trades = get_open_trades()

    # PnL no realizado
    unrealized_pnl = 0.0
    for t in open_trades:
        price = binance.get_ticker_price(t.symbol)
        if t.side == "BUY":
            unrealized_pnl += (price - t.entry_price) * t.quantity
        else:
            unrealized_pnl += (t.entry_price - price) * t.quantity

    total_value = balance + unrealized_pnl
    total_return = ((total_value - initial) / initial) * 100

    return {
        "balance":        round(balance, 2),
        "unrealized_pnl": round(unrealized_pnl, 4),
        "total_value":    round(total_value, 2),
        "initial":        initial,
        "total_return":   round(total_return, 2),
        "open_trades":    len(open_trades),
    }
