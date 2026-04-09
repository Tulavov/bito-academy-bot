import threading
import os

def run_bot():
    print("🤖 Telegram bot ishga tushmoqda...")
    try:
        from bot import main
        main()
    except Exception as e:
        print(f"Bot xatolik: {e}")

if name == "main":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    from app import app
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Web server ishga tushdi: port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
