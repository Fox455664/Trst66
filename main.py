import os
import asyncio
import aiohttp
import aiofiles
import threading
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import NoActiveGroupCall, AlreadyJoinedError
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types import AudioQuality
from pytgcalls.types import Update
from pytgcalls.types.stream import StreamAudioEnded
from youtubesearchpython.__future__ import VideosSearch
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# ==========================================
# 1. إعدادات السيرفر (Koyeb Keep-Alive)
# ==========================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Online!", 200

def run_web():
    # تشغيل سيرفر فلاسك على البورت 8000
    web_app.run(host='0.0.0.0', port=8000)

# ==========================================
# 2. إعدادات البوت (ضع بياناتك هنا)
# ==========================================
API_ID = 25761783
API_HASH = "7770de22ee036afb30a99d449c51f4b8"
BOT_TOKEN = "8017670938:AAGURw0_kEKdZ_bYAYKs24RedQsfkve9Aiw"

SOURCE_NAME = "Caesar Music"
COOKIES_FILE = "cookies/cookies2.txt"

# ==========================================
# 3. تهيئة العملاء
# ==========================================
app = Client(
    "music_bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call_py = PyTgCalls(app)

# قوائم التشغيل
playlist = {}
titles = {}
playing_now = {}

# ==========================================
# 4. الدوال المساعدة
# ==========================================

async def download_yt(link):
    """تحميل الرابط المباشر باستخدام yt-dlp"""
    if not os.path.exists(COOKIES_FILE):
        print(f"⚠️ Warning: {COOKIES_FILE} not found!")
    
    command = [
        "yt-dlp", "--cookies", COOKIES_FILE,
        "-g", "-f", "bestaudio", link
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return stdout.decode().strip()
    except Exception as e:
        print(f"DL Error: {e}")
    return None

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))

async def gen_thumb(videoid):
    filename = f"photos/{videoid}.jpg"
    if os.path.isfile(filename): return filename

    try:
        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1)
        res = (await results.next())["result"][0]
        thumb_url = res["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    with open(f"thumb{videoid}.png", "wb") as f:
                        f.write(data)

        image = Image.open(f"thumb{videoid}.png")
        image = changeImageSize(1280, 720, image)
        
        background = image.convert("RGBA").filter(filter=ImageFilter.BoxBlur(5))
        enhancer = ImageEnhance.Brightness(background)
        image = enhancer.enhance(0.6)
        
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        draw.text((40, 40), f"{SOURCE_NAME}", fill="white", font=font)
        
        if not os.path.exists("photos"): os.mkdir("photos")
        image.convert("RGB").save(filename)
        os.remove(f"thumb{videoid}.png")
        return filename
    except:
        return None

async def play_next(chat_id):
    if chat_id in playlist and playlist[chat_id]:
        link = playlist[chat_id].pop(0)
        title = titles[chat_id].pop(0)
        stream = AudioPiped(link, audio_parameters=AudioQuality.STUDIO)
        try:
            await call_py.change_stream(chat_id, stream)
            playing_now[chat_id] = title
        except: pass
    else:
        try:
            await call_py.leave_group_call(chat_id)
            if chat_id in playing_now: del playing_now[chat_id]
        except: pass

# ==========================================
# 5. أوامر البوت
# ==========================================

@app.on_message(filters.command(["شغل", "play"], prefixes=["/", ""]) & filters.group)
async def play_handler(client, message):
    chat_id = message.chat.id
    try:
        query = message.text.split(None, 1)[1]
    except:
        return await message.reply("❌ **اكتب اسم الأغنية!** مثال: `شغل فيروز`")

    msg = await message.reply("🔎 **جاري البحث...**")
    
    try:
        search = VideosSearch(query, limit=1)
        res = (await search.next())["result"][0]
        videoid = res["id"]
        title = res["title"]
        link = f"https://www.youtube.com/watch?v={videoid}"
        
        stream_link = await download_yt(link)
        if not stream_link:
            return await msg.edit("❌ **خطأ في التحميل!** تأكد من الكوكيز.")

        thumb = await gen_thumb(videoid)
        
        try:
            stream = AudioPiped(stream_link, audio_parameters=AudioQuality.STUDIO)
            await call_py.join_group_call(
                chat_id, stream, stream_type=StreamType().pulse_stream
            )
            playing_now[chat_id] = title
            await msg.delete()
            if thumb:
                await message.reply_photo(thumb, caption=f"✅ **تم التشغيل:** {title}")
            else:
                await message.reply(f"✅ **تم التشغيل:** {title}")
        except NoActiveGroupCall:
            await msg.edit("⚠️ **الكول مغلق!** يرجى فتح المكالمة الصوتية في الجروب أولاً.")
        except AlreadyJoinedError:
            playlist.setdefault(chat_id, []).append(stream_link)
            titles.setdefault(chat_id, []).append(title)
            await msg.delete()
            await message.reply(f"➕ **تمت الإضافة للقائمة:** {title}")
            
    except Exception as e:
        await msg.edit(f"❌ خطأ: {e}")

@app.on_message(filters.command(["تخطي", "skip"], prefixes=["/", ""]) & filters.group)
async def skip(client, message):
    if message.chat.id not in playing_now: return
    await message.reply("⏭ **تم التخطي**")
    await play_next(message.chat.id)

@app.on_message(filters.command(["ايقاف", "stop"], prefixes=["/", ""]) & filters.group)
async def stop(client, message):
    chat_id = message.chat.id
    if chat_id in playlist: playlist[chat_id].clear()
    try:
        await call_py.leave_group_call(chat_id)
        await message.reply("⏹ **تم الإيقاف**")
    except: pass

@call_py.on_stream_end()
async def on_end(client, update: Update):
    if isinstance(update, StreamAudioEnded):
        await play_next(update.chat_id)

# ==========================================
# 6. التشغيل النهائي
# ==========================================
async def main():
    print("🚀 Starting Bot & Server...")
    # تشغيل السيرفر في ثريد منفصل
    threading.Thread(target=run_web, daemon=True).start()
    
    await app.start()
    await call_py.start()
    print(f"✅ Logged in as: {app.me.first_name}")
    await idle()
    await call_py.stop()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
