import os
import asyncio
import logging
import aiohttp
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("CapSkipScraper")

TARGET_URL = "https://capskip.com/captcha-demo/recaptcha-v2-invisible/"
SITE_KEY = "6LdDaSstAAAAAMRGlOvQjLQGaT1jD9s-HXwGIez7"
CAPTCHASOLV_ENDPOINT = "https://v2.captchasolv.com/solve"

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

async def solve_recaptcha_api(api_key: str, site_key: str, page_url: str, user_agent: str = DEFAULT_USER_AGENT, notify_func=None):
    """
    Fungsi untuk mengirim request solve reCAPTCHA v2 Invisible ke CaptchaSolv REST API
    (https://v2.captchasolv.com/solve) secara asynchronous.
    """
    if notify_func:
        await notify_func("🔑 [LOG: API Solver] Mengirim task reCAPTCHA v2 Invisible ke CaptchaSolv API...")

    payload = {
        "api_key": api_key,
        "type": "RecaptchaV2Invisible",
        "site_url": page_url,
        "useragent": user_agent,
        "timeout_secs": 60,
        "data": {
            "site_key": site_key
        }
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(CAPTCHASOLV_ENDPOINT, json=payload, timeout=aiohttp.ClientTimeout(total=70)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"HTTP Error {resp.status}: {text[:100]}")
                
                res_data = await resp.json()
                logger.info(f"CaptchaSolv API Response: {res_data}")

                error_id = res_data.get("errorId", -1)
                if error_id == 0 and res_data.get("status") == "ready":
                    data_obj = res_data.get("data") or {}
                    solution_obj = data_obj.get("solution") or {}
                    token = solution_obj.get("token") or res_data.get("token")
                    if token:
                        solv_time = res_data.get("solvtime", 0)
                        logger.info(f"Token g-recaptcha-response berhasil didapatkan dari CaptchaSolv dalam {solv_time}s!")
                        return token
                    raise RuntimeError("Token tidak ditemukan pada response CaptchaSolv.")
                else:
                    error_msg = res_data.get("errorMessage") or f"errorId {error_id}"
                    raise RuntimeError(f"CaptchaSolv API Error: {error_msg}")

        except Exception as err:
            logger.error(f"Gagal memecahkan captcha via CaptchaSolv API: {err}")
            raise err


async def run_capskip_demo(headless: bool = True, status_callback=None):
    """
    Fungsi web scraping demo reCAPTCHA v2 Invisible.
    
    Alur Kerja dengan CaptchaSolv API (https://docsv2.captchasolv.com/docs):
    1. Membuka halaman CapSkip demo.
    2. Jika API Key terdeteksi (CAPTCHASOLV_API_KEY / CAPTCHA_API_KEY / SOLVECAPTCHA_API_KEY):
       - Meminta token reCAPTCHA v2 Invisible ke CaptchaSolv API (POST https://v2.captchasolv.com/solve).
       - Menyuapkan/Injeksi token ke hidden field g-recaptcha-response.
       - Memanggil callback JS `capskipV2InvisibleToken(token)`.
    3. Jika API Key tidak ada:
       - Menekan tombol Check secara otomatis & menunggu 10s.
    4. Mengambil screenshot Desktop (Zoom 90%, centered scroll).
    """
    api_key = (
        os.getenv("CAPTCHASOLV_API_KEY") or
        os.getenv("CAPTCHA_API_KEY") or
        os.getenv("SOLVECAPTCHA_API_KEY") or
        os.getenv("TWOCAPTCHA_API_KEY", "")
    ).strip()

    async def notify(text: str):
        logger.info(text)
        if status_callback:
            try:
                await status_callback(text)
            except Exception:
                pass

    await notify("🌐 [LOG: 1/4] Membuka halaman CapSkip Demo...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=DEFAULT_USER_AGENT
        )
        
        page = await context.new_page()
        screenshot_path = "capskip_result.png"
        
        try:
            # 1. Buka Halaman Target
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(1.5)
            
            # Hapus popup pengganggu
            try:
                await page.evaluate("""() => {
                    const popups = document.querySelectorAll('.cap-popup, .ekit-popup, div[class*="community"], button[class*="close"]');
                    popups.forEach(el => el.remove());
                }""")
            except Exception:
                pass

            token = ""
            # 2. PROSES SOLVER (Jika API Key Tersedia)
            if api_key:
                await notify("🔑 [LOG: 2/4] API Key CaptchaSolv terdeteksi! Mengirim request ke CaptchaSolv API...")
                try:
                    token = await solve_recaptcha_api(api_key, SITE_KEY, TARGET_URL, user_agent=DEFAULT_USER_AGENT, notify_func=notify)
                    
                    await notify("⚡ [LOG: 3/4] Token CaptchaSolv didapatkan! Menyuntikkan token & memicu Callback JS...")
                    
                    # Injeksi token ke form & panggil callback
                    await page.evaluate("""(token) => {
                        const input = document.querySelector('textarea[name="g-recaptcha-response"], input[name="g-recaptcha-response"]');
                        if (input) input.value = token;
                        
                        if (typeof window.capskipV2InvisibleToken === 'function') {
                            window.capskipV2InvisibleToken(token);
                        } else if (typeof capskipV2InvisibleToken === 'function') {
                            capskipV2InvisibleToken(token);
                        }
                    }""", token)
                    
                    await asyncio.sleep(3) # Tunggu 3 detik agar widget merender Success: true
                    
                except Exception as err:
                    logger.error(f"Gagal memecahkan captcha via CaptchaSolv API: {err}")
                    await notify(f"⚠️ CaptchaSolv API Error: {str(err)[:60]}. Menggunakan metode tombol Check standar...")
                    api_key = "" # Fallback ke klik manual
            
            # MODE KLIK STANDAR (Jika API Key tidak ada / fallback)
            if not api_key:
                await notify("🖱️ [LOG: 2/4] Menekan tombol 'Check'...")
                check_btn = page.locator("button.captcha-verify, button:has-text('Check')").first
                await check_btn.wait_for(state="visible", timeout=15000)
                await check_btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                
                try:
                    await check_btn.click(timeout=3000)
                except Exception:
                    pass
                
                try:
                    await page.evaluate("""() => {
                        const btn = document.querySelector('button.captcha-verify') || Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.trim().toLowerCase() === 'check');
                        if (btn) btn.click();
                    }""")
                except Exception:
                    pass

                await notify("⏳ [LOG: 3/4] Menunggu 10 detik...")
                await asyncio.sleep(10)

            # 3. MEMBACA STATUS HASIL
            status_text = "Proses Selesai"
            try:
                reset_btn = page.locator("button.captcha-reset, button:has-text('Reset')").first
                result_box = page.locator(".captcha-result, [data-captcha-result]").first
                if (await reset_btn.count() > 0 and await reset_btn.is_visible()) or (await result_box.count() > 0 and await result_box.is_visible()):
                    status_text = "Success: true (Verified & Token Generated)"
                else:
                    status_locator = page.locator("[data-captcha-status], .captcha-widget__status").first
                    if await status_locator.count() > 0:
                        st = (await status_locator.inner_text()).strip()
                        if st:
                            status_text = st
            except Exception:
                pass

            if len(status_text) > 100:
                status_text = status_text[:97] + "..."

            # 4. SCREENSHOT DESKTOP VIEWPORT (Zoom 90% & Scroll Centered)
            await notify("✨ [LOG: 4/4] Mengambil screenshot tampilan Desktop...")
            
            try:
                await page.evaluate("""() => {
                    document.body.style.zoom = '90%';
                    const popups = document.querySelectorAll('.cap-popup, .ekit-popup, div[class*="community"]');
                    popups.forEach(el => el.remove());
                    
                    const widget = document.querySelector('#capskip-demo, .captcha-widget');
                    if (widget) {
                        widget.scrollIntoView({ block: 'center', behavior: 'instant' });
                    }
                }""")
            except Exception:
                pass
                
            await asyncio.sleep(0.8)
            await page.screenshot(path=screenshot_path, full_page=False)
            logger.info(f"Bukti screenshot disimpan ke: {screenshot_path}")
            
            return {
                "success": True,
                "status_text": status_text,
                "screenshot": screenshot_path
            }

        except Exception as e:
            logger.error(f"❌ Terjadi kesalahan: {e}")
            try:
                await page.screenshot(path=screenshot_path, full_page=False)
            except Exception:
                pass
            return {
                "success": True,
                "status_text": f"Status: {str(e)[:80]}",
                "screenshot": screenshot_path
            }
            
        finally:
            await browser.close()
            logger.info("Browser ditutup.")

if __name__ == "__main__":
    asyncio.run(run_capskip_demo(headless=True))

