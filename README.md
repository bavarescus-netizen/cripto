# 🤖 CRYPTO SCALPING BOT — GUÍA COMPLETA

Bot de trading automático con Scalping + Swing + Meme Coins, desplegado en Railway con base de datos Neon PostgreSQL y control total desde Telegram.

---

## ⚡ CARACTERÍSTICAS

| Módulo | Descripción |
|--------|-------------|
| **Scalping RSI+BB** | Opera en 1m, RSI extremo + Bollinger Bands + MACD |
| **Scalping MACD** | Opera en 5m, cruce de MACD con confirmación EMA |
| **Swing Trading** | Opera en 1h/4h, tendencia macro con entrada en pullback |
| **Meme Breakout** | Detecta explosiones de meme coins en tiempo real |
| **Interés Compuesto** | Reinvierte % de ganancias automáticamente |
| **Aprendizaje** | Guarda señales y estadísticas por estrategia/par |

---

## 🛠️ PASO A PASO — CONFIGURACIÓN

### 1. Obtener Token de Telegram

1. Abre Telegram y busca **@BotFather**
2. Escribe `/newbot` y sigue los pasos
3. Copia el **token** (formato: `123456:ABCdef...`)
4. Busca **@userinfobot** y manda cualquier mensaje → copia tu **User ID**

---

### 2. Configurar Binance Testnet (DEMO)

1. Ve a [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Inicia sesión con tu cuenta de GitHub
3. Ve a **API Management** → **Create API Key**
4. Copia la **API Key** y el **Secret Key**
5. El testnet te da fondos virtuales automáticamente

---

### 3. Crear Base de Datos en Neon

1. Ve a [neon.tech](https://neon.tech) y crea una cuenta gratuita
2. Crea un nuevo proyecto: **"trading-bot-db"**
3. En el panel, ve a **Connection Details**
4. Copia la **Connection String** (formato: `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`)

---

### 4. Desplegar en Railway

1. Ve a [railway.app](https://railway.app) y conecta tu cuenta de GitHub
2. Sube este proyecto a un repositorio de GitHub
3. En Railway: **New Project → Deploy from GitHub Repo**
4. Selecciona tu repositorio
5. Ve a **Variables** y agrega:

```
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_ADMIN_ID=tu_user_id_aqui
BINANCE_API_KEY=tu_api_key_testnet
BINANCE_SECRET_KEY=tu_secret_key_testnet
BINANCE_TESTNET=true
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
INITIAL_CAPITAL=1000
MAX_RISK_PER_TRADE=2
COMPOUND_REINVEST=80
MAX_OPEN_TRADES=3
BOT_MODE=demo
```

6. Railway desplegará automáticamente con Docker ✅

---

## 📱 COMANDOS DE TELEGRAM

| Comando | Descripción |
|---------|-------------|
| `/start` | Menú principal interactivo |
| `/menu` | Abrir menú principal |
| `/set risk 1.5` | Cambiar riesgo por trade a 1.5% |
| `/set max_trades 5` | Máximo 5 trades simultáneos |
| `/set capital 500` | Cambiar capital inicial |
| `/set compound 90` | Reinvertir 90% de ganancias |
| `/set scalp_tp 1.0` | TP scalping al 1% |
| `/set scalp_sl 0.5` | SL scalping al 0.5% |
| `/set swing_tp 4.0` | TP swing al 4% |
| `/set swing_sl 2.0` | SL swing al 2% |
| `/set pairs BTCUSDT,ETHUSDT` | Pares principales activos |
| `/set meme_pairs DOGEUSDT,PEPE` | Pares meme activos |

---

## 🧠 ESTRATEGIAS EXPLICADAS

### ⚡ Scalping RSI + Bollinger Bands (1 minuto)
- **Entrada LONG**: RSI < 32, precio toca BB inferior, MACD sube, Stoch < 25, volumen alto
- **Entrada SHORT**: RSI > 68, precio toca BB superior, MACD baja, Stoch > 75
- **TP/SL**: 0.8% / 0.4% (configurable)
- **Duración**: 2-15 minutos

### 📊 Scalping MACD Cross (5 minutos)
- **Señal**: Cruce del histograma MACD (cambia de signo)
- **Confirmación**: Alineación de EMA 9/21/50, ADX > 20
- **TP/SL**: 0.8% / 0.4%
- **Duración**: 5-30 minutos

### 📈 Swing Trading (1h con confirmación 4h)
- **Tendencia**: EMA 50 > EMA 200 en 4h con ADX > 25
- **Entrada**: Pullback en 1h con RSI 35-60, MACD positivo
- **TP/SL**: 3% / 1.5%
- **Duración**: Horas a días

### 🚀 Meme Coin Breakout (5 minutos)
- **Filtro**: Cambio > 5% en 24h, volumen > 500k USDT
- **Señal**: Volumen actual 2x la media, RSI no extremo
- **TP/SL**: 5% / 2.5% (más agresivo por mayor volatilidad)
- **Detección dinámica**: Busca automáticamente nuevos movers

---

## 💰 INTERÉS COMPUESTO

El bot reinvierte automáticamente el **80%** de cada ganancia (configurable).

| Capital Inicial | Mensual +5% | Mensual +10% | Mensual +15% |
|----------------|-------------|--------------|--------------|
| $100 | $162 (6 meses) | $177 (6 meses) | $313 (1 año) |
| $500 | $672 (6 meses) | $885 (1 año) | $2,439 (1 año) |
| $1,000 | $1,344 (6 meses) | $3,138 (2 años) | $4,652 (2 años) |

---

## 🏗️ ARQUITECTURA

```
main.py
├── src/
│   ├── telegram_bot.py    # Bot de Telegram con menús
│   ├── scanner.py         # Motor de escaneo de mercado
│   ├── strategies.py      # RSI, MACD, Swing, Meme
│   ├── executor.py        # Apertura/cierre con risk mgmt
│   ├── binance_client.py  # API Binance (testnet/live)
│   └── database.py        # Neon PostgreSQL con SQLAlchemy
├── Dockerfile             # Para Railway
├── railway.toml           # Config de despliegue
└── requirements.txt       # Dependencias Python
```

---

## ⚠️ IMPORTANTE — MODO DEMO vs LIVE

- **BINANCE_TESTNET=true**: Opera en testnet con fondos virtuales ✅
- **BINANCE_TESTNET=false**: Opera con dinero REAL ⚠️

**Nunca actives LIVE sin haber probado extensamente en DEMO.**

---

## 🔧 DESARROLLO LOCAL

```bash
# Clonar e instalar
pip install -r requirements.txt

# Copiar y configurar variables
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar
python main.py
```

Para desarrollo local sin Neon, usa SQLite (automático si DATABASE_URL no apunta a PostgreSQL).
