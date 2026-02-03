import os, threading, asyncio, subprocess, sys, importlib
from flask import Flask

# 1. سيرفر Koyeb الوهمي
app = Flask(__name__)
@app.route('/')
def health(): return "Bot is Online!", 200
def run_web(): app.run(host='0.0.0.0', port=8000)
threading.Thread(target=run_web, daemon=True).start()

# 2. مثبت المكتبات الإجباري (حل نهائي)
def fix_libs():
    libs = ["unidecode", "pytube", "telethon", "oldpyro", "flask", "pyro-listener", "youtube-search", "httpx==0.24.1"]
    for lib in libs:
        try:
            name = lib.split("==")[0].replace("-", "_")
            importlib.import_module(name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
            importlib.invalidate_caches()

fix_libs()

# 3. تشغيل البوت
from bot import start_zombiebot
async def start():
    print("🔥 بوت فوكس المطور ينطلق الآن...")
    await start_zombiebot()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start())
