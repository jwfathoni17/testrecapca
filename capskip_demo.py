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
    
    Fitur Peningkatan:
    - status_callback: Mengirim log progress secara real-time ke bot Telegram.
    - Polling deteksi tombol 'Reset' & box 'VERIFICATION RESPONSE' (Success: true).
    - Centering scroll & Zoom 90% presisi sesuai contoh screenshot sukses.
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
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        try:
            # 1. Buka Halaman Target
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(1)
            
            # Apply Zoom 90% & Hapus Popup Pengganggu
            try:
                await page.evaluate("""() => {
                    document.body.style.zoom = '90%';
                    const popups = document.querySelectorAll('.cap-popup, .ekit-popup, div[class*="community"], button[class*="close"]');
                    popups.forEach(el => el.remove());
                }""")
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
            
            # 4. Menunggu Hasil Verifikasi (Deteksi Tombol Reset & VERIFICATION RESPONSE)
            await notify("⏳ [LOG: 3/4] Menunggu proses verifikasi reCAPTCHA & kemunculan tombol Reset...")
            
            status_text = ""
            recaptcha_token = ""
            is_verifying = True
            
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 30:
                # 1. Deteksi apakah tombol Reset sudah muncul
                reset_btn = page.locator("button.captcha-reset, button:has-text('Reset')").first
                reset_visible = await reset_btn.count() > 0 and await reset_btn.is_visible()
                
                # 2. Deteksi box VERIFICATION RESPONSE (.captcha-result)
                result_box = page.locator(".captcha-result, [data-captcha-result]").first
                result_visible = await result_box.count() > 0 and await result_box.is_visible()
                result_text = ""
                if result_visible:
                    result_text = await result_box.inner_text()

                # 3. Deteksi token di hidden textarea/input
                token_input = page.locator('textarea[name="g-recaptcha-response"], input[name="g-recaptcha-response"]').first
                if await token_input.count() > 0:
                    recaptcha_token = await token_input.input_value()
                
                # Cek teks status umum di widget
                status_locator = page.locator("[data-captcha-status], .captcha-widget__status").first
                if await status_locator.count() > 0:
                    status_text = (await status_locator.inner_text()).strip()

                # Jika tombol Reset ATAU box VERIFICATION RESPONSE muncul -> VERIFIKASI BERHASIL!
                if reset_visible or (result_visible and ("success" in result_text.lower() or "true" in result_text.lower())):
                    is_verifying = False
                    status_text = "✅ Success: true (Verified & Token Generated)"
                    logger.info("Tombol Reset / Verification Response 'Success: true' berhasil terdeteksi!")
                    break
                    
                if status_text and "verifying" not in status_text.lower():
                    is_verifying = False
                    logger.info(f"Verifikasi selesai dengan status: '{status_text}'")
                    break

                await asyncio.sleep(1.0)
            
            if is_verifying:
                if not status_text or status_text.lower() == "verifying...":
                    status_text = "⚠️ Verifying (Google Invisible reCAPTCHA dipicu / Menunggu Solver)"
                logger.warning(f"Waktu tunggu habis. Status: '{status_text}'")

            # 5. Screenshot Desktop Viewport Centered (Zoom 90%)
            await notify("✨ [LOG: 4/4] Mengambil screenshot tampilan Desktop...")
            screenshot_path = "capskip_result.png"
            
            # Posisikan Scroll presisi ke tengah widget (seperti pada contoh screenshot sukses)
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
            
            # Screenshot Desktop Viewport
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
            await page.screenshot(path=error_screenshot, full_page=False)
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
