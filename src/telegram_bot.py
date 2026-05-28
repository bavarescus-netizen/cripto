"""
telegram_bot.py - Bot de Telegram con Menú Interactivo Completo
Maneja todos los comandos, botones inline y notificaciones
"""

import os
import asyncio
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from dotenv import load_dotenv

from src.database import (
    get_config, set_config, get_open_trades,
    get_stats_summary, SessionLocal, Trade
)
from src.executor import get_portfolio_summary, open_trade, check_and_close_trades
from src.scanner import run_full_scan, get_market_overview
from src.strategies import format_signal_message

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ─── VERIFICACIÓN DE ADMIN ───────────────────────────────────────────────────

def admin_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else 0
        if uid != ADMIN_ID:
            await update.message.reply_text("⛔ No tienes acceso a este bot.")
            return
        return await func(update, ctx)
    return wrapper


# ─── MENÚ PRINCIPAL ──────────────────────────────────────────────────────────

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Portfolio",    callback_data="menu_portfolio"),
            InlineKeyboardButton("📡 Mercado",      callback_data="menu_market"),
        ],
        [
            InlineKeyboardButton("⚡ Escanear",     callback_data="menu_scan"),
            InlineKeyboardButton("📋 Operaciones",  callback_data="menu_trades"),
        ],
        [
            InlineKeyboardButton("🤖 Bot Control",  callback_data="menu_bot"),
            InlineKeyboardButton("⚙️ Configurar",   callback_data="menu_config"),
        ],
        [
            InlineKeyboardButton("📈 Estadísticas", callback_data="menu_stats"),
            InlineKeyboardButton("🎓 Aprendizaje",  callback_data="menu_learning"),
        ],
    ])


WELCOME_MSG = (
    "🤖 *CRYPTO SCALPING BOT*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "Sistema de trading automático con:\n"
    "• ⚡ Scalping 1m/5m (RSI + MACD)\n"
    "• 📈 Swing Trading 1h/4h\n"
    "• 🚀 Detección Meme Coins\n"
    "• 💰 Interés Compuesto Automático\n"
    "• 🎓 Aprendizaje por histórico\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "Selecciona una opción:"
)


@admin_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )


@admin_only
async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 *Menú Principal*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )


# ─── CALLBACK HANDLER PRINCIPAL ──────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    # Enrutar a la función correcta
    handlers = {
        "menu_portfolio":  show_portfolio,
        "menu_market":     show_market,
        "menu_scan":       show_scan_menu,
        "menu_trades":     show_open_trades,
        "menu_bot":        show_bot_control,
        "menu_config":     show_config_menu,
        "menu_stats":      show_stats,
        "menu_learning":   show_learning,
        "back_main":       show_main_menu,
        # Bot control
        "bot_start":       bot_start_trading,
        "bot_stop":        bot_stop_trading,
        "bot_status":      bot_status,
        "bot_close_all":   bot_close_all,
        # Scan
        "scan_scalp":      scan_scalp_now,
        "scan_swing":      scan_swing_now,
        "scan_meme":       scan_meme_now,
        "scan_full":       scan_full_now,
        # Config
        "cfg_risk":        cfg_show_risk,
        "cfg_pairs":       cfg_show_pairs,
        "cfg_strategies":  cfg_show_strategies,
        "cfg_compound":    cfg_show_compound,
        # Toggle strategies
        "toggle_scalp":    toggle_scalp,
        "toggle_swing":    toggle_swing,
        "toggle_meme":     toggle_meme,
        # Trades
        "trades_history":  show_trade_history,
        "trades_close_all": close_all_trades,
    }

    fn = handlers.get(data)
    if fn:
        await fn(query, ctx)
    elif data.startswith("close_trade_"):
        trade_id = int(data.replace("close_trade_", ""))
        await close_single_trade(query, ctx, trade_id)
    else:
        await query.edit_message_text("❓ Opción no reconocida.")


def back_button(target="back_main"):
    return [[InlineKeyboardButton("◀️ Volver", callback_data=target)]]


# ─── PORTFOLIO ───────────────────────────────────────────────────────────────

async def show_portfolio(query, ctx):
    pf = get_portfolio_summary()
    mode = "🔵 DEMO" if os.getenv("BINANCE_TESTNET", "true") == "true" else "🔴 LIVE"
    pnl_emoji = "🟢" if pf["total_return"] >= 0 else "🔴"

    msg = (
        f"💼 *PORTFOLIO*  {mode}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Balance USDT: `{pf['balance']:,.2f}`\n"
        f"📊 PnL Abierto: `{pf['unrealized_pnl']:+.4f}`\n"
        f"💰 Valor Total: `{pf['total_value']:,.2f}`\n"
        f"🏦 Capital Inicial: `{pf['initial']:,.2f}`\n"
        f"{pnl_emoji} Retorno Total: `{pf['total_return']:+.2f}%`\n"
        f"📋 Ops. Abiertas: `{pf['open_trades']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 `{datetime.utcnow().strftime('%H:%M:%S UTC')}`"
    )
    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Actualizar", callback_data="menu_portfolio")],
        *back_button()
    ])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


# ─── MERCADO ─────────────────────────────────────────────────────────────────

async def show_market(query, ctx):
    overview = get_market_overview()
    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Actualizar", callback_data="menu_market")],
        [InlineKeyboardButton("⚡ Escanear ahora", callback_data="scan_full")],
        *back_button()
    ])
    await query.edit_message_text(overview, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


# ─── OPERACIONES ABIERTAS ─────────────────────────────────────────────────────

async def show_open_trades(query, ctx):
    trades = get_open_trades()
    if not trades:
        msg = "📋 *OPERACIONES*\n━━━━━━━━━━━━━━━━━━━━━━\nNo hay operaciones abiertas."
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton("📜 Ver Historial", callback_data="trades_history")],
            *back_button()
        ])
    else:
        msg = f"📋 *OPERACIONES ABIERTAS* ({len(trades)})\n━━━━━━━━━━━━━━━━━━━━━━\n"
        buttons = []
        for t in trades:
            price = 0
            try:
                from src.binance_client import binance
                price = binance.get_ticker_price(t.symbol)
            except Exception:
                pass
            if t.side == "BUY":
                pnl = (price - t.entry_price) * t.quantity if price else 0
            else:
                pnl = (t.entry_price - price) * t.quantity if price else 0
            emoji = "🟢" if pnl >= 0 else "🔴"
            msg += (
                f"\n{emoji} `{t.symbol}` | {t.side}\n"
                f"  Entrada: `{t.entry_price}` → Actual: `{price}`\n"
                f"  PnL: `{pnl:+.4f}` USDT | {t.strategy}\n"
                f"  TP: `{t.take_profit}` | SL: `{t.stop_loss}`\n"
            )
            buttons.append([InlineKeyboardButton(
                f"❌ Cerrar {t.symbol}", callback_data=f"close_trade_{t.id}"
            )])
        buttons += [
            [InlineKeyboardButton("❌ Cerrar Todo", callback_data="trades_close_all")],
            *back_button()
        ]
        kbd = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def show_trade_history(query, ctx):
    with SessionLocal() as db:
        trades = db.query(Trade).filter(Trade.status == "CLOSED").order_by(Trade.closed_at.desc()).limit(10).all()
    if not trades:
        msg = "📜 *HISTORIAL*\nNo hay operaciones cerradas aún."
    else:
        msg = "📜 *ÚLTIMAS 10 OPERACIONES*\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for t in trades:
            emoji = "✅" if t.pnl and t.pnl > 0 else "❌"
            msg += (
                f"{emoji} `{t.symbol}` | {t.side} | {t.strategy}\n"
                f"  PnL: `{t.pnl:+.4f}` ({t.pnl_pct:+.2f}%)\n"
            )
    kbd = InlineKeyboardMarkup(back_button("menu_trades"))
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def close_single_trade(query, ctx, trade_id: int):
    from src.database import SessionLocal, Trade
    from src.executor import _close_trade
    with SessionLocal() as db:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if trade and trade.status == "OPEN":
            from src.binance_client import binance
            price = binance.get_ticker_price(trade.symbol)
            _close_trade(db, trade, price, "Manual desde Telegram")
    await show_open_trades(query, ctx)


async def close_all_trades(query, ctx):
    from src.database import get_open_trades
    from src.executor import _close_trade
    from src.binance_client import binance
    trades = get_open_trades()
    with SessionLocal() as db:
        for t in trades:
            price = binance.get_ticker_price(t.symbol)
            trade_obj = db.query(Trade).filter(Trade.id == t.id).first()
            if trade_obj:
                _close_trade(db, trade_obj, price, "Cierre masivo Telegram")
    await query.edit_message_text("✅ Todas las operaciones cerradas.", reply_markup=InlineKeyboardMarkup(back_button("menu_trades")))


# ─── ESCANEO ─────────────────────────────────────────────────────────────────

async def show_scan_menu(query, ctx):
    msg = "🔍 *ESCANEO DE MERCADO*\nElige el tipo de análisis:"
    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Scalping (1m/5m)",  callback_data="scan_scalp")],
        [InlineKeyboardButton("📈 Swing (1h/4h)",     callback_data="scan_swing")],
        [InlineKeyboardButton("🚀 Meme Coins",        callback_data="scan_meme")],
        [InlineKeyboardButton("🌐 Escaneo Completo",  callback_data="scan_full")],
        *back_button()
    ])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def scan_scalp_now(query, ctx):
    await query.edit_message_text("⚡ *Escaneando scalping...* ⏳", parse_mode=ParseMode.MARKDOWN)
    pairs = get_config("active_pairs", "BTCUSDT,ETHUSDT,SOLUSDT").split(",")
    from src.scanner import scan_scalping
    signals = scan_scalping(pairs)
    await _show_signals(query, signals, "SCALPING")


async def scan_swing_now(query, ctx):
    await query.edit_message_text("📈 *Escaneando swing...* ⏳", parse_mode=ParseMode.MARKDOWN)
    pairs = get_config("active_pairs", "BTCUSDT,ETHUSDT,SOLUSDT").split(",")
    from src.scanner import scan_swing
    signals = scan_swing(pairs)
    await _show_signals(query, signals, "SWING")


async def scan_meme_now(query, ctx):
    await query.edit_message_text("🚀 *Escaneando meme coins...* ⏳", parse_mode=ParseMode.MARKDOWN)
    meme_pairs = get_config("meme_pairs", "DOGEUSDT,PEPEUSDT,SHIBUSDT").split(",")
    from src.scanner import scan_memes
    signals = scan_memes(meme_pairs)
    await _show_signals(query, signals, "MEME COINS")


async def scan_full_now(query, ctx):
    await query.edit_message_text("🌐 *Escaneo completo...* ⏳\nAnalizando todos los pares...", parse_mode=ParseMode.MARKDOWN)
    from src.scanner import run_full_scan
    results = run_full_scan()
    all_signals = results["scalp"] + results["swing"] + results["meme"]
    await _show_signals(query, all_signals, "COMPLETO")


async def _show_signals(query, signals, label: str):
    if not signals:
        msg = f"🔍 *ESCANEO {label}*\n━━━━━━━━━━━━━━━━━━━━━━\nNo se encontraron señales en este momento.\n\nEl mercado está en zona neutral."
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Volver a escanear", callback_data="menu_scan")],
            *back_button()
        ])
    else:
        msg = f"🔍 *ESCANEO {label}* — {len(signals)} señal(es)\n━━━━━━━━━━━━━━━━━━━━━━\n"
        buttons = []
        for sig in signals[:5]:  # Máximo 5 señales
            msg += "\n" + format_signal_message(sig) + "\n"
            buttons.append([InlineKeyboardButton(
                f"▶️ Ejecutar {sig.symbol} {sig.direction}",
                callback_data=f"exec_{sig.symbol}_{sig.direction}_{sig.strategy}"
            )])
        buttons += back_button("menu_scan")
        kbd = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


# ─── CONTROL DEL BOT ─────────────────────────────────────────────────────────

async def show_bot_control(query, ctx):
    is_running = ctx.bot_data.get("trading_active", False)
    mode = "🔵 DEMO" if os.getenv("BINANCE_TESTNET", "true") == "true" else "🔴 LIVE"
    status_icon = "🟢 ACTIVO" if is_running else "🔴 DETENIDO"

    msg = (
        f"🤖 *CONTROL DEL BOT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Estado: {status_icon}\n"
        f"Modo: {mode}\n"
        f"Escaneo: cada 60 segundos\n"
        f"Max trades abiertos: {get_config('max_open_trades', '3')}\n"
        f"Riesgo por trade: {get_config('max_risk_per_trade', '2')}%\n"
    )
    kbd = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Iniciar Bot",   callback_data="bot_start"),
            InlineKeyboardButton("⏸ Detener Bot",   callback_data="bot_stop"),
        ],
        [
            InlineKeyboardButton("📊 Estado",        callback_data="bot_status"),
            InlineKeyboardButton("❌ Cerrar Todo",   callback_data="bot_close_all"),
        ],
        *back_button()
    ])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def bot_start_trading(query, ctx):
    ctx.bot_data["trading_active"] = True
    await query.edit_message_text(
        "✅ *Bot ACTIVADO*\nEl bot comenzará a escanear y operar automáticamente cada minuto.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(back_button("menu_bot"))
    )


async def bot_stop_trading(query, ctx):
    ctx.bot_data["trading_active"] = False
    await query.edit_message_text(
        "⏸ *Bot DETENIDO*\nNo se abrirán nuevas operaciones. Las existentes siguen activas.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(back_button("menu_bot"))
    )


async def bot_status(query, ctx):
    await show_bot_control(query, ctx)


async def bot_close_all(query, ctx):
    await close_all_trades(query, ctx)


# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────

async def show_config_menu(query, ctx):
    msg = "⚙️ *CONFIGURACIÓN*\nAjusta los parámetros del bot:"
    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Riesgo & Capital",    callback_data="cfg_risk")],
        [InlineKeyboardButton("🪙 Pares Activos",       callback_data="cfg_pairs")],
        [InlineKeyboardButton("🧠 Estrategias",         callback_data="cfg_strategies")],
        [InlineKeyboardButton("💰 Interés Compuesto",   callback_data="cfg_compound")],
        *back_button()
    ])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def cfg_show_risk(query, ctx):
    risk     = get_config("max_risk_per_trade", "2")
    max_ops  = get_config("max_open_trades", "3")
    capital  = get_config("initial_capital", "1000")
    msg = (
        f"📊 *RIESGO & CAPITAL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Capital inicial: `{capital} USDT`\n"
        f"Riesgo por trade: `{risk}%`\n"
        f"Máx. operaciones: `{max_ops}`\n\n"
        f"Para cambiar, usa:\n"
        f"`/set risk 1.5` — Cambiar riesgo\n"
        f"`/set max_trades 5` — Máx. trades\n"
        f"`/set capital 500` — Capital inicial"
    )
    kbd = InlineKeyboardMarkup(back_button("menu_config"))
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def cfg_show_pairs(query, ctx):
    pairs = get_config("active_pairs", "BTCUSDT,ETHUSDT,SOLUSDT")
    memes = get_config("meme_pairs", "DOGEUSDT,PEPEUSDT,SHIBUSDT,BONKUSDT")
    msg = (
        f"🪙 *PARES ACTIVOS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Principales:\n`{pairs}`\n\n"
        f"Meme Coins:\n`{memes}`\n\n"
        f"Usa:\n"
        f"`/set pairs BTCUSDT,ETHUSDT` — Cambiar pares\n"
        f"`/set meme_pairs DOGEUSDT,SHIBUSDT`"
    )
    kbd = InlineKeyboardMarkup(back_button("menu_config"))
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def cfg_show_strategies(query, ctx):
    scalp_on = get_config("scalp_enabled", "true") == "true"
    swing_on  = get_config("swing_enabled", "true") == "true"
    meme_on   = get_config("meme_enabled",  "true") == "true"
    msg = (
        f"🧠 *ESTRATEGIAS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Scalping: {'✅ ON' if scalp_on else '❌ OFF'}\n"
        f"📈 Swing: {'✅ ON' if swing_on else '❌ OFF'}\n"
        f"🚀 Meme Coins: {'✅ ON' if meme_on else '❌ OFF'}"
    )
    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'✅' if scalp_on else '❌'} Scalping",
            callback_data="toggle_scalp"
        )],
        [InlineKeyboardButton(
            f"{'✅' if swing_on else '❌'} Swing",
            callback_data="toggle_swing"
        )],
        [InlineKeyboardButton(
            f"{'✅' if meme_on else '❌'} Meme Coins",
            callback_data="toggle_meme"
        )],
        *back_button("menu_config")
    ])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def cfg_show_compound(query, ctx):
    reinvest = get_config("compound_reinvest", "80")
    scalp_tp = get_config("scalp_tp_pct", "0.8")
    scalp_sl = get_config("scalp_sl_pct", "0.4")
    swing_tp = get_config("swing_tp_pct", "3.0")
    swing_sl = get_config("swing_sl_pct", "1.5")
    msg = (
        f"💰 *INTERÉS COMPUESTO & TP/SL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Reinversión de ganancias: `{reinvest}%`\n\n"
        f"⚡ Scalping:\n  TP: `{scalp_tp}%` | SL: `{scalp_sl}%`\n\n"
        f"📈 Swing:\n  TP: `{swing_tp}%` | SL: `{swing_sl}%`\n\n"
        f"Usa:\n"
        f"`/set compound 90` — % reinversión\n"
        f"`/set scalp_tp 1.0` — TP scalping\n"
        f"`/set swing_tp 4.0` — TP swing"
    )
    kbd = InlineKeyboardMarkup(back_button("menu_config"))
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


async def toggle_scalp(query, ctx):
    current = get_config("scalp_enabled", "true") == "true"
    set_config("scalp_enabled", "false" if current else "true")
    await cfg_show_strategies(query, ctx)


async def toggle_swing(query, ctx):
    current = get_config("swing_enabled", "true") == "true"
    set_config("swing_enabled", "false" if current else "true")
    await cfg_show_strategies(query, ctx)


async def toggle_meme(query, ctx):
    current = get_config("meme_enabled", "true") == "true"
    set_config("meme_enabled", "false" if current else "true")
    await cfg_show_strategies(query, ctx)


# ─── ESTADÍSTICAS ─────────────────────────────────────────────────────────────

async def show_stats(query, ctx):
    stats = get_stats_summary()
    pf    = get_portfolio_summary()

    msg = (
        f"📈 *ESTADÍSTICAS TOTALES*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Total operaciones: `{stats['total']}`\n"
        f"✅ Ganadoras: `{stats['wins']}`\n"
        f"❌ Perdedoras: `{stats['losses']}`\n"
        f"🎯 Win Rate: `{stats['win_rate']}%`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 PnL Total: `{stats['total_pnl']:+.4f} USDT`\n"
        f"🏆 Mejor trade: `{stats.get('best_trade', 0):+.4f} USDT`\n"
        f"💥 Peor trade: `{stats.get('worst_trade', 0):+.4f} USDT`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Capital actual: `{pf['total_value']:,.2f} USDT`\n"
        f"📊 Retorno total: `{pf['total_return']:+.2f}%`"
    )
    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Actualizar", callback_data="menu_stats")],
        *back_button()
    ])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


# ─── APRENDIZAJE ──────────────────────────────────────────────────────────────

async def show_learning(query, ctx):
    from src.database import LearningStats
    with SessionLocal() as db:
        stats = db.query(LearningStats).order_by(LearningStats.total_trades.desc()).limit(8).all()

    if not stats:
        msg = "🎓 *APRENDIZAJE*\nAún no hay suficientes datos. El bot aprende con cada operación."
    else:
        msg = "🎓 *ANÁLISIS DE ESTRATEGIAS*\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for s in stats:
            wr = round((s.winning_trades / max(s.total_trades, 1)) * 100, 1)
            emoji = "🏆" if wr > 55 else ("⚠️" if wr > 45 else "❌")
            msg += (
                f"\n{emoji} `{s.symbol}` — {s.strategy}\n"
                f"  Trades: {s.total_trades} | WR: {wr}% | PnL: {s.total_pnl:+.2f}\n"
            )
        msg += "\n\n💡 El bot prioriza automáticamente las estrategias con mayor win rate."

    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Actualizar", callback_data="menu_learning")],
        *back_button()
    ])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)


# ─── VOLVER AL MENÚ PRINCIPAL ────────────────────────────────────────────────

async def show_main_menu(query, ctx):
    await query.edit_message_text(
        WELCOME_MSG,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )


# ─── COMANDO SET ──────────────────────────────────────────────────────────────

SET_KEY_MAP = {
    "risk":        "max_risk_per_trade",
    "max_trades":  "max_open_trades",
    "capital":     "initial_capital",
    "compound":    "compound_reinvest",
    "scalp_tp":    "scalp_tp_pct",
    "scalp_sl":    "scalp_sl_pct",
    "swing_tp":    "swing_tp_pct",
    "swing_sl":    "swing_sl_pct",
    "pairs":       "active_pairs",
    "meme_pairs":  "meme_pairs",
}


@admin_only
async def cmd_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "📝 Uso: `/set <clave> <valor>`\n\n"
            "Claves: `risk, max_trades, capital, compound,\nscalp_tp, scalp_sl, swing_tp, swing_sl,\npairs, meme_pairs`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    key_alias = args[0].lower()
    value     = " ".join(args[1:])
    db_key    = SET_KEY_MAP.get(key_alias)

    if not db_key:
        await update.message.reply_text(f"❌ Clave `{key_alias}` no reconocida.", parse_mode=ParseMode.MARKDOWN)
        return

    set_config(db_key, value)
    await update.message.reply_text(
        f"✅ Configuración actualizada:\n`{key_alias}` = `{value}`",
        parse_mode=ParseMode.MARKDOWN
    )


# ─── AUTO-TRADING LOOP ────────────────────────────────────────────────────────

async def auto_trading_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Job que corre cada 60s: escanear mercado, abrir y revisar trades"""
    if not ctx.bot_data.get("trading_active", False):
        return

    admin_id = ADMIN_ID
    if not admin_id:
        return

    async def notify(msg: str):
        try:
            await ctx.bot.send_message(admin_id, msg, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    # 1. Revisar trades abiertos (TP/SL)
    def sync_notify(msg): asyncio.create_task(notify(msg))
    check_and_close_trades(sync_notify)

    # 2. Escanear nuevas oportunidades
    from src.scanner import run_full_scan
    results = run_full_scan()
    all_signals = results["scalp"] + results["swing"] + results["meme"]

    open_count = len(get_open_trades())
    max_trades = int(get_config("max_open_trades", "3"))

    for signal in all_signals:
        if open_count >= max_trades:
            break
        if signal.strength < 60:
            continue

        trade = open_trade(signal)
        if trade:
            open_count += 1
            msg = (
                f"🔔 *NUEVA OPERACIÓN ABIERTA*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                + format_signal_message(signal)
            )
            await notify(msg)


# ─── SETUP Y ARRANQUE ────────────────────────────────────────────────────────

def build_app() -> Application:
    from src.database import init_db
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("menu",   cmd_menu))
    app.add_handler(CommandHandler("set",    cmd_set))

    # Callbacks de botones inline
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Job de auto-trading cada 60 segundos
    app.job_queue.run_repeating(auto_trading_job, interval=60, first=10)

    return app


def run_bot():
    app = build_app()
    logger.info("🤖 Bot iniciado — esperando órdenes en Telegram...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
