import os
import logging
import asyncio
import uvicorn
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from capskip_demo import run_capskip_demo

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CapSkipBot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

app = FastAPI()
telegram_app = None

def get_test_keyboard():
    """
    Membuat Inline Keyboard dengan 1 tombol 'Test Scraping' yang diberi hiasan emoji berwarna.
    """
    keyboard = [
        [InlineKeyboardButton("🧪 🟢 Test Scraping 🚀", callback_data="test_scraping")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk command /start.
    """
    welcome_text = (
        "🤖 <b>Bot Scraping CapSkip Demo</b>\n\n"
        "Klik tombol di bawah ini untuk memulai pengujian web scraping:\n"
        "Bot akan membuka halaman target, menekan tombol Check, dan mengirimkan screenshot buktinya ke sini!"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_test_keyboard(),
        parse_mode="HTML"
    )

async def handle_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler saat tombol 'Test Scraping' ditekan.
    Menggunakan update_status kontinu (edit 1 pesan yang sama) seperti di bot.py.
    """
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    
    # 1. Kirim 1 pesan status awal yang akan terus di-update
    status_msg = await query.message.reply_text(
        "🌐 <b>[LOG: 1/4] Membuka halaman CapSkip Demo...</b>",
        parse_mode="HTML"
    )
    
    async def update_status(text: str):
        try:
            await context.bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=status_msg.message_id,
                parse_mode="HTML"
            )
        except Exception:
            pass

    try:
        # 2. Jalankan fungsi web scraping dengan status_callback
        res = await run_capskip_demo(headless=True, status_callback=update_status)
        
        screenshot_path = res.get("screenshot")
        status_text = res.get("status_text", "Tombol Check Ditekan")
        
        # 3. Kirim foto hasil ke Telegram jika berhasil
        if res.get("success") and screenshot_path and os.path.exists(screenshot_path):
            caption = (
                "✅ <b>WEB SCRAPING SELESAI!</b>\n\n"
                "🌐 <b>Target URL</b>: <code>https://capskip.com/captcha-demo/recaptcha-v2-invisible/</code>\n"
                f"📊 <b>Status Web Akhir</b>: <code>{status_text}</code>\n\n"
                "🖼️ <i>Bukti screenshot halaman terlampir di bawah:</i>"
            )
            
            with open(screenshot_path, "rb") as photo_file:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_file,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=get_test_keyboard()
                )
            
            # Hapus pesan status sementara agar chat bersih (tidak menumpuk)
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
            except Exception:
                pass
                
        else:
            error_msg = res.get("error", "Gagal melakukan scraping")
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"❌ <b>Gagal Memproses Scraping:</b>\n<code>{error_msg}</code>",
                parse_mode="HTML",
                reply_markup=get_test_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error pada callback handler: {e}")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"❌ <b>Terjadi Kesalahan:</b>\n<code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=get_test_keyboard()
        )

@app.get("/")
async def health_check():
    """
    Endpoint Health Check untuk Railway.
    """
    return Response(content="CapSkip Bot is running smoothly on Railway Webhook!", status_code=200)

@app.post("/")
async def webhook(request: Request):
    """
    Endpoint Webhook Telegram.
    Railway akan menerima payload HTTP POST dari Telegram dan meneruskannya ke Telegram Application.
    """
    global telegram_app
    try:
        data = await request.json()
        if telegram_app:
            update = Update.de_json(data, telegram_app.bot)
            if update:
                await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Error pada endpoint webhook: {e}")
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    """
    Inisialisasi Telegram Application saat FastAPI server dimulai.
    """
    global telegram_app
    if not TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN belum diset di environment variables!")
        return

    telegram_app = Application.builder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(handle_test_callback, pattern="^test_scraping$"))
    
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Bot Telegram Webhook berhasil di-inisialisasi!")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean shutdown Telegram application saat server mati.
    """
    global telegram_app
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("capskip_bot:app", host="0.0.0.0", port=port, reload=False)
