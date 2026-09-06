import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("CapSkipScraper")

TARGET_URL = "https://capskip.com/captcha-demo/recaptcha-v2-invisible/"

async def run_capskip_demo(headless: bool = True, status_callback=None):
    """
    Fungsi utama untuk melakukan web scraping pada demo reCAPTCHA v2 Invisible.
    
    Fitur Tambahan:
    - status_callback: Mengirim log progress secara real-time ke bot Telegram (edit 1 pesan secara kontinu).
    - Polling status verifikasi hingga status tidak lagi 'Verifying...' (timeout 12 detik).
    - Penutupan popup/modal pengganggu agar hasil screenshot bersih.
    """
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
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        try:
            # 1. Buka Halaman Target
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(1)
            
            # Coba tutup popup/modal newsletter atau iklan pengganggu jika ada
            try:
                close_btn = page.locator("button.cap-popup-close, .ekit-popup-close, [aria-label='Close']").first
                if await close_btn.count() > 0 and await close_btn.is_visible():
                    await close_btn.click(force=True)
                    await asyncio.sleep(0.5)
            except Exception:
                pass
            
            # 2. Cari Tombol 'Check'
            await notify("🖱️ [LOG: 2/4] Mencari dan menekan tombol 'Check'...")
            check_button_selector = "button.captcha-verify"
            check_button = page.locator(check_button_selector).first
            await check_button.wait_for(state="visible", timeout=15000)
            
            await check_button.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            
            # 3. Klik Tombol Check
            await check_button.click()
            
            # 4. Menunggu Hasil Verifikasi (Jeda waktu polling hingga status bukan 'Verifying...')
            await notify("⏳ [LOG: 3/4] Menunggu proses verifikasi reCAPTCHA selesai (pengecekan status valid)...")
            
            status_text = ""
            recaptcha_token = ""
            is_verifying = True
            
            # Polling selama maksimal 12 detik
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 12:
                # Cek teks status di widget
                status_locator = page.locator("[data-captcha-status], .captcha-widget__status").first
                if await status_locator.count() > 0:
                    status_text = (await status_locator.inner_text()).strip()
                
                # Cek token di hidden textarea/input
                token_input = page.locator('textarea[name="g-recaptcha-response"], input[name="g-recaptcha-response"]').first
                if await token_input.count() > 0:
                    recaptcha_token = await token_input.input_value()
                
                # Cek elemen hasil (.captcha-result)
                result_box = page.locator(".captcha-result, [data-captcha-result]").first
                result_text = ""
                if await result_box.count() > 0 and await result_box.is_visible():
                    result_text = await result_box.inner_text()

                # Jika status sudah bukan "verifying" lagi, atau token sudah ada, atau result box terlihat
                if status_text and "verifying" not in status_text.lower():
                    is_verifying = False
                    logger.info(f"Proses verifikasi selesai dengan status: '{status_text}'")
                    break
                    
                if recaptcha_token:
                    is_verifying = False
                    logger.info("Token reCAPTCHA terdeteksi.")
                    break
                    
                if result_text:
                    is_verifying = False
                    status_text = result_text.strip()
                    break

                await asyncio.sleep(0.8)
            
            # Jika setelah timeout 12 detik masih 'Verifying...'
            if is_verifying:
                if status_text.lower() == "verifying...":
                    status_text = "Verifying (Google Challenge dipicu / Membutuhkan Captcha Solver)"
                logger.warning(f"Waktu tunggu habis. Status akhir: '{status_text}'")

            # 5. Screenshot Bukti Hasil
            await notify("✨ [LOG: 4/4] Mengambil screenshot bukti & menyelesaikan proses...")
            screenshot_path = "capskip_result.png"
            
            demo_container = page.locator("#capskip-demo, .captcha-widget").first
            if await demo_container.count() > 0:
                await demo_container.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await demo_container.screenshot(path=screenshot_path)
            else:
                await page.screenshot(path=screenshot_path, full_page=False)
                
            logger.info(f"Bukti screenshot disimpan ke: {screenshot_path}")
            
            return {
                "success": True,
                "status_text": status_text if status_text else "Proses Selesai",
                "token": recaptcha_token,
                "screenshot": screenshot_path,
                "is_verifying": is_verifying
            }

        except Exception as e:
            logger.error(f"❌ Terjadi kesalahan saat scraping: {e}")
            error_screenshot = "capskip_error.png"
            await page.screenshot(path=error_screenshot)
            return {
                "success": False,
                "error": str(e),
                "screenshot": error_screenshot
            }
            
        finally:
            await browser.close()
            logger.info("Browser ditutup.")

if __name__ == "__main__":
    asyncio.run(run_capskip_demo(headless=True))
