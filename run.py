import threading
import asyncio
import os
import sys

def run_flask():
    """Flask web server ni ishga tushirish"""
    from app import app
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Web server ishga tushdi: port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def run_bot():
    """Telegram botni ishga tushirish"""
    print("🤖 Telegram bot ishga tushmoqda...")
    from bot import main
    main()

if __name__ == "__main__":
    # Flask ni alohida threadda ishga tushiramiz
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Bot asosiy threadda ishlaydi
    run_bot()
