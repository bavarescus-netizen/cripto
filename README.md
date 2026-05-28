# 🤖 CRYPTO SCALPING BOT — GUÍA COMPLETA

Bot de trading automático: Scalping + Swing + Meme Coins.
Desplegado en **Render** (gratis) + **Neon** PostgreSQL + control desde **Telegram**.
UptimeRobot hace ping cada 10 min para mantenerlo despierto 24/7.

---

## ⚡ CARACTERÍSTICAS

| Módulo | Descripción |
|--------|-------------|
| Scalping RSI+BB | Opera en 1m, RSI extremo + Bollinger Bands + MACD |
| Scalping MACD | Opera en 5m, cruce de MACD con confirmación EMA |
| Swing Trading | Opera en 1h/4h, tendencia macro con entrada en pullback |
| Meme Breakout | Detecta explosiones de meme coins en tiempo real |
| Interés Compuesto | Reinvierte % de ganancias automáticamente |
| Aprendizaje | Guarda señales y estadísticas por estrategia/par |

---

## 🛠️ PASO A PASO

### PASO 1 — Telegram Bot

1. Abre Telegram → busca **@BotFather**
2. Escribe `/newbot` → sigue los pasos → copia el **token**
3. Busca **@userinfobot** → envía cualquier mensaje → copia tu **User ID**

---

### PASO 2 — Binance Testnet (Demo gratuito)

1. Ve a `testnet.binancefuture.com`
2. Inicia sesión con GitHub
3. **API Management** → **Create API Key**
4. Copia la **API Key** y el **Secret Key**
5. El testnet te da fondos virtuales automáticamente ✅

---

### PASO 3 — Neon PostgreSQL (Base de datos gratis)

1. Ve a `neon.tech` → crea cuenta gratuita
2. Nuevo proyecto: `trading-bot-db`
3. **Connection Details** → copia la **Connection String**
   Formato: `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`

---

### PASO 4 — Render (Hosting gratis, sin tarjeta)

1. Ve a `render.com` → crea cuenta con GitHub
2. **New** → **Web Service**
3. Conecta tu repositorio de GitHub (sube este proyecto primero)
4. Configuración:
   - **Name**: `crypto-scalping-bot`
   - **Runtime**: Docker
   - **Plan**: Free
5. En **Environment Variables** agrega:

```
TELEGRAM_BOT_TOKEN     = tu_token_aqui
TELEGRAM_ADMIN_ID      = tu_user_id_aqui
BINANCE_API_KEY        = tu_api_key_testnet
BINANCE_SECRET_KEY     = tu_secret_key_testnet
BINANCE_TESTNET        = true
DATABASE_URL           = postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
INITIAL_CAPITAL        = 1000
MAX_RISK_PER_TRADE     = 2
COMPOUND_REINVEST      = 80
MAX_OPEN_TRADES        = 3
BOT_MODE               = demo
PORT                   = 10000
```

6. Clic en **Create Web Service** → espera el deploy (~3 min)
7. Anota la URL que te da Render: `https://crypto-scalping-bot.onrender.com`

---

### PASO 5 — UptimeRobot (Ping cada 10 min para no dormir)

Render duerme el servicio si no recibe tráfico. UptimeRobot lo despierta gratis.

1. Ve a `uptimerobot.com` → crea cuenta gratuita
2. **Add New Monitor**:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: `Crypto Bot`
   - **URL**: `https://crypto-scalping-bot.onrender.com/health`
   - **Monitoring Interval**: 10 minutes
3. Clic en **Create Monitor** ✅

El bot ya nunca dormirá. UptimeRobot además te avisa por email si el bot cae.

---

## 📱 COMANDOS DE TELEGRAM

| Comando | Descripción |
|---------|-------------|
| `/start` | Menú principal interactivo |
| `/menu` | Abrir menú principal |
| `/set risk 1.5` | Cambiar riesgo por trade a 1.5% |
| `/set max_trades 5` | Máximo 5 trades simultáneos |
| `/set capital 500` | Capital inicial |
| `/set compound 90` | Reinvertir 90% de ganancias |
| `/set scalp_tp 1.0` | Take Profit scalping al 1% |
| `/set scalp_sl 0.5` | Stop Loss scalping al 0.5% |
| `/set swing_tp 4.0` | Take Profit swing al 4% |
| `/set swing_sl 2.0` | Stop Loss swing al 2% |
| `/set pairs BTCUSDT,ETHUSDT` | Pares principales |
| `/set meme_pairs DOGEUSDT,PEPE` | Pares meme |

---

## 🧠 ESTRATEGIAS

### Scalping RSI + BB (1 minuto)
- LONG: RSI < 32, precio en BB inferior, MACD sube, volumen alto
- SHORT: RSI > 68, precio en BB superior, MACD baja
- TP/SL: 0.8% / 0.4%

### Scalping MACD Cross (5 minutos)
- Cruce del histograma MACD + alineación EMA 9/21/50 + ADX > 20
- TP/SL: 0.8% / 0.4%

### Swing Trading (1h confirmado en 4h)
- Tendencia: EMA50 > EMA200 en 4h con ADX > 25
- Entrada en pullback con RSI 35-60
- TP/SL: 3% / 1.5%

### Meme Coin Breakout (5 minutos)
- Cambio > 5% en 24h, volumen > 500k USDT
- Volumen actual 2x la media
- TP/SL: 5% / 2.5%

---

## 🏗️ ARCHIVOS DEL PROYECTO

```
main.py                    Punto de entrada
src/
  health_server.py         Servidor HTTP para Render + ping
  telegram_bot.py          Bot Telegram con menús interactivos
  scanner.py               Escaneo de mercado cada 60s
  strategies.py            4 estrategias de trading
  executor.py              Apertura/cierre con risk management
  binance_client.py        API Binance Testnet
  database.py              Neon PostgreSQL con SQLAlchemy
Dockerfile                 Para Render
render.yaml                Config de Render
```

---

## ⚠️ DEMO vs LIVE

- `BINANCE_TESTNET=true` → Opera con fondos virtuales ✅
- `BINANCE_TESTNET=false` → Opera con dinero REAL ⚠️

Nunca actives LIVE sin haber probado extensamente en DEMO.

---

## 🔧 DESARROLLO LOCAL

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus credenciales
python main.py
```
