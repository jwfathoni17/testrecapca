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

async def solve_recaptcha_api(api_key: str, site_key: str, page_url: str, notify_func=None):
    """
    Fungsi untuk mengirim request solve reCAPTCHA v2 Invisible ke SolveCaptcha / 2Captcha API
    menggunakan aiohttp secara asynchronous.
    """
    # Menentukan base URL (SolveCaptcha / 2Captcha)
    base_url = "https://api.solvecaptcha.com" if "solvecaptcha" in api_key.lower() else "https://2captcha.com"
    in_url = f"{base_url}/in.php"
    res_url = f"{base_url}/res.php"

    if notify_func:
        await notify_func(f"🔑 [LOG: API Solver] Mengirim sitekey ke {base_url}...")

    async with aiohttp.ClientSession() as session:
        # 1. Kirim Task Captcha
        payload = {
            "key": api_key,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "invisible": "1",
            "json": "1"
        }
        
        async with session.post(in_url, data=payload) as resp:
            data = await resp.json()
            if data.get("status") != 1:
                raise RuntimeError(f"Gagal membuat task solver API: {data.get('request')}")
            task_id = data.get("request")
            logger.info(f"Task Captcha Solver berhasil dibuat! Task ID: {task_id}")

        if notify_func:
            await notify_func(f"⏳ [LOG: API Solver] Task ID: {task_id}. Menunggu token dari solver...")

        # 2. Polling Hasil Token (Setiap 5 detik hingga maksimal 60 detik)
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < 60:
            await asyncio.sleep(5)
            params = {
                "key": api_key,
                "action": "get",
                "id": task_id,
                "json": "1"
            }
            async with session.get(res_url, params=params) as res_resp:
                res_data = await res_resp.json()
                if res_data.get("status") == 1:
                    token = res_data.get("request")
                    logger.info("Token g-recaptcha-response berhasil didapatkan dari Solver API!")
                    return token
                elif res_data.get("request") != "CAPCHA_NOT_READY":
                    raise RuntimeError(f"Error Solver API: {res_data.get('request')}")

        raise TimeoutError("Waktu tunggu token dari Captcha Solver API habis (Timeout 60s).")


async def run_capskip_demo(headless: bool = True, status_callback=None):
    """
    Fungsi web scraping demo reCAPTCHA v2 Invisible.
    
    Alur Kerja dengan API Solver (SolveCaptcha / 2Captcha):
    1. Membuka halaman CapSkip demo.
    2. Jika API Key terdeteksi (SOLVECAPTCHA_API_KEY / TWOCAPTCHA_API_KEY):
       - Meminta token reCAPTCHA ke Solver API (invisible=1).
       - Menyuapkan/Injeksi token ke hidden field g-recaptcha-response.
       - Memanggil callback JS `capskipV2InvisibleToken(token)`.
    3. Jika API Key tidak ada:
       - Menekan tombol Check secara otomatis & menunggu 10s.
    4. Mengambil screenshot Desktop (Zoom 90%, centered scroll).
    """
    api_key = os.getenv("SOLVECAPTCHA_API_KEY") or os.getenv("TWOCAPTCHA_API_KEY") or os.getenv("CAPTCHA_API_KEY", "")

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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
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
                await notify("🔑 [LOG: 2/4] API Key terdeteksi! Mengirim request ke Captcha Solver API...")
                try:
                    token = await solve_recaptcha_api(api_key, SITE_KEY, TARGET_URL, notify_func=notify)
                    
                    await notify("⚡ [LOG: 3/4] Token didapatkan! Menyuntikkan token & memicu Callback JS...")
                    
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
                    logger.error(f"Gagal memecahkan captcha via API Solver: {err}")
                    await notify(f"⚠️ Solver API Error: {str(err)[:60]}. Menggunakan metode tombol Check standar...")
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
