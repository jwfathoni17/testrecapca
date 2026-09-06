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
    Fungsi web scraping demo reCAPTCHA v2 Invisible.
    
    Alur Kerja yang Dijamin Anti-Crash:
    1. Membuka URL target & meng-set zoom 90%.
    2. Menekan tombol 'Check' (dengan fallback DOM agar tidak timeout).
    3. Menunggu tepat 10 detik.
    4. Mengambil screenshot Desktop (Zoom 90%, centered scroll).
    5. Mengembalikan file screenshot secara konsisten ke bot Telegram.
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
        screenshot_path = "capskip_result.png"
        
        try:
            # 1. Buka Halaman Target
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            
            # Apply Zoom 90% & Hapus Popup Pengganggu
            try:
                await page.evaluate("""() => {
                    document.body.style.zoom = '90%';
                    const popups = document.querySelectorAll('.cap-popup, .ekit-popup, div[class*="community"], button[class*="close"]');
                    popups.forEach(el => el.remove());
                }""")
            except Exception:
                pass
            
            # 2. Cari & Klik Tombol 'Check' tanpa timeout
            await notify("🖱️ [LOG: 2/4] Menekan tombol 'Check'...")
            
            button_clicked = False
            try:
                check_btn = page.locator("button.captcha-verify, button:has-text('Check'), .captcha-widget button").first
                if await check_btn.count() > 0:
                    await check_btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await check_btn.click(force=True, timeout=5000)
                    button_clicked = True
            except Exception as e:
                logger.warning(f"Klik standar locator gagal ({e}), menggunakan DOM click fallback...")
            
            if not button_clicked:
                try:
                    await page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        const target = btns.find(b => b.innerText && b.innerText.trim().toLowerCase() === 'check');
                        if (target) target.click();
                    }""")
                    button_clicked = True
                except Exception:
                    pass

            # 3. Menunggu Tepat 10 Detik
            await notify("⏳ [LOG: 3/4] Menunggu tepat 10 detik setelah menekan Check...")
            await asyncio.sleep(10)
            
            # 4. Membaca Status Singkat
            status_text = "Check ditekankan (Menunggu 10s)"
            try:
                status_locator = page.locator("[data-captcha-status], .captcha-widget__status").first
                if await status_locator.count() > 0:
                    st = (await status_locator.inner_text()).strip()
                    if st:
                        status_text = st
            except Exception:
                pass
                
            if len(status_text) > 100:
                status_text = status_text[:97] + "..."

            # 5. Screenshot Desktop Viewport Centered (Zoom 90%)
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
                
            await asyncio.sleep(1.0)
            
            # Screenshot Desktop Viewport (full_page=False)
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
                "success": True, # Tetap return True agar screenshot jika ada tetap dikirim
                "status_text": f"Error: {str(e)[:80]}",
                "screenshot": screenshot_path
            }
            
        finally:
            await browser.close()
            logger.info("Browser ditutup.")

if __name__ == "__main__":
    asyncio.run(run_capskip_demo(headless=True))
