# 🕷️ Panduan Belajar Web Scraping: CapSkip reCAPTCHA v2 Invisible & Deploy Railway

Project ini dibuat khusus untuk mempelajari teknik **Web Scraping** menggunakan **Python Playwright** pada web demo [CapSkip reCAPTCHA v2 Invisible](https://capskip.com/captcha-demo/recaptcha-v2-invisible/), serta cara mendeploy-nya di **Railway.app**.

---

## 📁 Struktur File Project

- `capskip_bot.py` : Bot Telegram dengan 1 tombol Inline Keyboard ("🧪 Test Scraping") yang secara otomatis memicu web scraping dan mengembalikan foto screenshot ke chat Telegram.
- `capskip_demo.py` : Script utama Python Playwright yang membuka web, mencari tombol "Check", menekannya, dan mengambil screenshot.
- `requirements.txt` : Daftar library Python (`playwright`, `python-telegram-bot`, dll).
- `Dockerfile` : Konfigurasi container Linux Playwright untuk deployment di Railway.
- `README.md` : Panduan belajar dan langkah deployment.

---

## 🤖 Cara Kerja Integrasi Bot Telegram

1. Pengguna mengirim `/start` ke Bot Telegram.
2. Bot menampilkan pesan salam beserta **1 Inline Keyboard Button** (dihias emoji visual): `[🧪 🟢 Test Scraping 🚀]`.
3. Saat pengguna menekan tombol tersebut:
   - Bot mengirim pesan status awal (`⏳ Memproses...`).
   - Playwright menjalankan `run_capskip_demo()`.
   - Screenshot `capskip_result.png` dikirim langsung ke pengguna Telegram beserta tombol inline keyboard tersebut.

---

## 🚀 Cara Menjalankan Secara Lokal (Local Testing)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Set Environment Variable Bot Token**:
   - Windows PowerShell: `$env:TELEGRAM_BOT_TOKEN="BOT_TOKEN_KAMU"`
   - CMD: `set TELEGRAM_BOT_TOKEN=BOT_TOKEN_KAMU`

3. **Jalankan Bot**:
   ```bash
   python capskip_bot.py
   ```

---

## ☁️ Cara Deploy ke Railway.app

1. **Push ke GitHub**:
   Upload folder project ini (`capskip_bot.py`, `capskip_demo.py`, `requirements.txt`, `Dockerfile`) ke repository GitHub Anda.

2. **Buat Service Baru di Railway**:
   - Buka dashboard [Railway.app](https://railway.app/).
   - Klik **New Project** -> **Deploy from GitHub repo**.
   - Pilih repository project ini.

3. **Set Variables di Railway**:
   - Di tab **Variables** di Railway, tambahkan:
     - `TELEGRAM_BOT_TOKEN` = Token bot Telegram Anda.

4. **Set Webhook Telegram**:
   - Dapatkan Domain URL publik dari Railway (misal: `https://your-app.up.railway.app`).
   - Set Webhook bot Telegram Anda dengan membuka URL berikut di browser:
     ```
     https://api.telegram.org/bot<TOKEN_TELEGRAM_KAMU>/setWebhook?url=https://your-app.up.railway.app/
     ```

5. **Deploy Otomatis**:
   - Railway mendeteksi `Dockerfile` dan secara otomatis menjalankan `capskip_bot.py` via FastAPI / Uvicorn server 24/7 di cloud.
