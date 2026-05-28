"""
main.py - Punto de entrada del Crypto Scalping Bot
Arranca el health server (para Render) y luego el bot de Telegram
"""

from src.health_server import start_health_server
from src.telegram_bot import run_bot

if __name__ == "__main__":
    # 1. Levantar servidor HTTP para Render + UptimeRobot ping
    start_health_server()

    # 2. Arrancar el bot de Telegram (bloquea el hilo principal)
    run_bot()
