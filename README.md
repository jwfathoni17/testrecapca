# 🕷️ Panduan Belajar Web Scraping: CapSkip reCAPTCHA v2 Invisible & Deploy Railway

Project ini dibuat khusus untuk mempelajari teknik **Web Scraping** menggunakan **Python Playwright** pada web demo [CapSkip reCAPTCHA v2 Invisible](https://capskip.com/captcha-demo/recaptcha-v2-invisible/), serta memecahkan captcha secara otomatis menggunakan **CaptchaSolv REST API** (`https://docsv2.captchasolv.com/docs`) dan mendeploy-nya di **Railway.app**.

---

## 📁 Struktur File Project

- `capskip_bot.py` : Bot Telegram dengan 1 tombol Inline Keyboard ("🧪 Test Scraping") yang secara otomatis memicu web scraping dan mengembalikan foto screenshot ke chat Telegram.
- `capskip_demo.py` : Script utama Python Playwright yang meminta token reCAPTCHA ke **CaptchaSolv REST API**, menyuntikkan token ke field `g-recaptcha-response`, memicu callback JS `capskipV2InvisibleToken(token)`, dan mengambil screenshot.
- `requirements.txt` : Daftar library Python (`playwright`, `python-telegram-bot`, `aiohttp`, `fastapi`, `uvicorn`).
- `Dockerfile` : Konfigurasi container Linux Playwright untuk deployment di Railway.
- `README.md` : Panduan belajar dan langkah deployment.

---

## 🔑 Integrasi CaptchaSolv REST API

- **Endpoint**: `POST https://v2.captchasolv.com/solve`
- **Captcha Type**: `RecaptchaV2Invisible`
- **Site Key**: `6LdDaSstAAAAAMRGlOvQjLQGaT1jD9s-HXwGIez7`
- **Variabel Environment**: `CAPTCHASOLV_API_KEY`

---

## 🤖 Cara Kerja Integrasi Bot Telegram

1. Pengguna mengirim `/start` ke Bot Telegram.
2. Bot menampilkan pesan salam beserta **1 Inline Keyboard Button**: `[🧪 🟢 Test Scraping 🚀]`.
3. Saat pengguna menekan tombol tersebut:
   - Bot mengirim pesan status awal yang terus diperbarui (`[LOG: 1/4] ...`).
   - Playwright & CaptchaSolv API menyelesaikan captcha invisible secara otomatis.
   - Screenshot `capskip_result.png` dikirim langsung ke pengguna Telegram beserta tombol inline keyboard tersebut.

---

## 🚀 Cara Menjalankan Secara Lokal (Local Testing)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Set Environment Variable**:
   - Windows PowerShell:
     ```powershell
     $env:TELEGRAM_BOT_TOKEN="BOT_TOKEN_KAMU"
     $env:CAPTCHASOLV_API_KEY="API_KEY_CAPTCHASOLV_KAMU"
     ```
   - CMD:
     ```cmd
     set TELEGRAM_BOT_TOKEN=BOT_TOKEN_KAMU
     set CAPTCHASOLV_API_KEY=API_KEY_CAPTCHASOLV_KAMU
     ```

3. **Jalankan Bot**:
   ```bash
   python capskip_bot.py
   ```

---

## ☁️ Cara Deploy ke Railway.app

1. **Push ke GitHub**:
   Upload folder project ini ke repository GitHub Anda.

2. **Buat Service Baru di Railway**:
   - Buka dashboard [Railway.app](https://railway.app/).
   - Klik **New Project** -> **Deploy from GitHub repo**.
   - Pilih repository project ini.

3. **Set Variables di Railway**:
   - Di tab **Variables** di Railway, tambahkan:
     - `TELEGRAM_BOT_TOKEN` = Token bot Telegram Anda.
     - `CAPTCHASOLV_API_KEY` = Key CaptchaSolv Anda ($0.10 credit).

4. **Set Webhook Telegram**:
   - Dapatkan Domain URL publik dari Railway (misal: `https://your-app.up.railway.app`).
   - Set Webhook bot Telegram Anda dengan membuka URL berikut di browser:
     ```
     https://api.telegram.org/bot<TOKEN_TELEGRAM_KAMU>/setWebhook?url=https://your-app.up.railway.app/
     ```

5. **Deploy Otomatis**:
   - Railway mendeteksi `Dockerfile` dan secara otomatis menjalankan `capskip_bot.py` via FastAPI / Uvicorn server 24/7 di cloud.

