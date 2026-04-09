import threading
import os
import time

def run_bot():
    time.sleep(2)
    print("🤖 Telegram bot ishga tushmoqda...")
    try:
        from bot import main
        main()
    except Exception as e:
        print(f"❌ Bot xatolik: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    from app import app
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Web server port {port} da ishga tushdi")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
