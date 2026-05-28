"""
database.py - Gestión de base de datos con Neon PostgreSQL
Almacena operaciones, historial, configuración y estadísticas de aprendizaje
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, 
    Boolean, DateTime, Text, JSON, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# ─── MODELOS ────────────────────────────────────────────────────────────────

class Trade(Base):
    """Registro de cada operación ejecutada"""
    __tablename__ = "trades"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    order_id      = Column(BigInteger, unique=True, nullable=False)
    symbol        = Column(String(20), nullable=False)          # BTC/USDT
    side          = Column(String(5), nullable=False)           # BUY | SELL
    strategy      = Column(String(30), nullable=False)          # scalp_1m | swing_4h
    timeframe     = Column(String(10), nullable=False)          # 1m | 5m | 1h | 4h
    entry_price   = Column(Float, nullable=False)
    exit_price    = Column(Float, nullable=True)
    quantity      = Column(Float, nullable=False)
    take_profit   = Column(Float, nullable=True)
    stop_loss     = Column(Float, nullable=True)
    pnl           = Column(Float, nullable=True, default=0.0)
    pnl_pct       = Column(Float, nullable=True, default=0.0)
    status        = Column(String(15), default="OPEN")          # OPEN | CLOSED | CANCELLED
    signal_data   = Column(JSON, nullable=True)                 # Indicadores al momento de entrar
    opened_at     = Column(DateTime, default=datetime.utcnow)
    closed_at     = Column(DateTime, nullable=True)
    is_demo       = Column(Boolean, default=True)

class BotConfig(Base):
    """Configuración dinámica del bot (editable desde Telegram)"""
    __tablename__ = "bot_config"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    key                 = Column(String(50), unique=True, nullable=False)
    value               = Column(Text, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PortfolioSnapshot(Base):
    """Historial del capital para gráfico de crecimiento"""
    __tablename__ = "portfolio_snapshots"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    balance     = Column(Float, nullable=False)
    open_pnl    = Column(Float, default=0.0)    # PnL operaciones abiertas
    total_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

class MarketSignal(Base):
    """Señales detectadas (con o sin operación abierta) — para aprendizaje"""
    __tablename__ = "market_signals"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    symbol         = Column(String(20), nullable=False)
    timeframe      = Column(String(10), nullable=False)
    signal_type    = Column(String(30), nullable=False)     # rsi_oversold | macd_cross | etc
    direction      = Column(String(5), nullable=False)       # LONG | SHORT
    strength       = Column(Float, nullable=True)            # 0-100
    price_at_signal = Column(Float, nullable=False)
    indicators     = Column(JSON, nullable=True)
    was_profitable = Column(Boolean, nullable=True)          # Se llena al cerrar
    detected_at    = Column(DateTime, default=datetime.utcnow)

class LearningStats(Base):
    """Estadísticas de aprendizaje por estrategia/símbolo"""
    __tablename__ = "learning_stats"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    symbol         = Column(String(20), nullable=False)
    strategy       = Column(String(30), nullable=False)
    timeframe      = Column(String(10), nullable=False)
    total_trades   = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    total_pnl      = Column(Float, default=0.0)
    avg_win        = Column(Float, default=0.0)
    avg_loss       = Column(Float, default=0.0)
    best_hours     = Column(JSON, nullable=True)     # Horas con más win rate
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ─── CONEXIÓN ────────────────────────────────────────────────────────────────

def get_engine():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./trading_bot.db")
    # Neon requiere SSL; SQLite para desarrollo local
    if "neon.tech" in db_url or "postgresql" in db_url:
        engine = create_engine(
            db_url,
            poolclass=NullPool,
            connect_args={"sslmode": "require"} if "neon.tech" in db_url else {}
        )
    else:
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return engine

engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    """Crear todas las tablas si no existen"""
    Base.metadata.create_all(bind=engine)
    _seed_default_config()
    print("✅ Base de datos inicializada")

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _seed_default_config():
    """Insertar configuración inicial si la tabla está vacía"""
    with SessionLocal() as db:
        defaults = {
            "initial_capital":    "1000",
            "max_risk_per_trade": "2",
            "compound_reinvest":  "80",
            "max_open_trades":    "3",
            "scalp_enabled":      "true",
            "swing_enabled":      "true",
            "meme_enabled":       "true",
            "active_pairs":       "BTCUSDT,ETHUSDT,SOLUSDT",
            "meme_pairs":         "DOGEUSDT,PEPEUSDT,SHIBUSDT,BONKUSDT",
            "scalp_tp_pct":       "0.8",
            "scalp_sl_pct":       "0.4",
            "swing_tp_pct":       "3.0",
            "swing_sl_pct":       "1.5",
            "min_volume_usdt":    "500000",
        }
        for key, value in defaults.items():
            existing = db.query(BotConfig).filter(BotConfig.key == key).first()
            if not existing:
                db.add(BotConfig(key=key, value=value))
        db.commit()

# ─── HELPERS ────────────────────────────────────────────────────────────────

def get_config(key: str, default=None):
    with SessionLocal() as db:
        row = db.query(BotConfig).filter(BotConfig.key == key).first()
        return row.value if row else default

def set_config(key: str, value: str):
    with SessionLocal() as db:
        row = db.query(BotConfig).filter(BotConfig.key == key).first()
        if row:
            row.value = value
            row.updated_at = datetime.utcnow()
        else:
            db.add(BotConfig(key=key, value=str(value)))
        db.commit()

def get_open_trades():
    with SessionLocal() as db:
        return db.query(Trade).filter(Trade.status == "OPEN").all()

def get_stats_summary():
    with SessionLocal() as db:
        trades = db.query(Trade).filter(Trade.status == "CLOSED").all()
        if not trades:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0, "total_pnl": 0}
        wins   = [t for t in trades if t.pnl and t.pnl > 0]
        losses = [t for t in trades if t.pnl and t.pnl <= 0]
        return {
            "total":     len(trades),
            "wins":      len(wins),
            "losses":    len(losses),
            "win_rate":  round(len(wins) / len(trades) * 100, 1) if trades else 0,
            "total_pnl": round(sum(t.pnl for t in trades if t.pnl), 2),
            "best_trade": round(max((t.pnl for t in trades if t.pnl), default=0), 2),
            "worst_trade": round(min((t.pnl for t in trades if t.pnl), default=0), 2),
        }
