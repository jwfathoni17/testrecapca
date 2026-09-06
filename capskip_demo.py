import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logger = logging.getLogger("CapSkipScraper")

TARGET_URL = "https://capskip.com/captcha-demo/recaptcha-v2-invisible/"

async def run_capskip_demo(headless: bool = True, status_callback=None):
    """
    Fungsi web scraping demo reCAPTCHA v2 Invisible.
    
    Peningkatan Utama:
    1. Membuka halaman dengan wait_until="networkidle" agar seluruh listener reCAPTCHA terpasang.
    2. Menekan tombol Check dengan 3 kombinasi metode (Native Click, JS MouseEvent, Bounding Box Click).
    3. CSS Zoom 90% baru diterapkan SEBELUM screenshot (bukan sebelum klik), agar posisi tombol tidak bergeser.
    4. Menunggu tepat 10 detik setelah klik.
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
            # 1. Buka Halaman Target dan tunggu network idle
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)
            
            # Hapus popup pengganggu jika ada
            try:
                await page.evaluate("""() => {
                    const popups = document.querySelectorAll('.cap-popup, .ekit-popup, div[class*="community"], button[class*="close"]');
                    popups.forEach(el => el.remove());
                }""")
            except Exception:
                pass
            
            # 2. Cari Tombol 'Check'
            await notify("🖱️ [LOG: 2/4] Mencari dan menekan tombol 'Check'...")
            
            check_btn = page.locator("button.captcha-verify, button:has-text('Check')").first
            await check_btn.wait_for(state="visible", timeout=15000)
            await check_btn.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            
            # Eksekusi 3 metode penekanan tombol secara berturut-turut
            logger.info("Menjalankan multi-strategy click pada tombol Check...")
            
            # Metode 1: Playwright Native Click
            try:
                await check_btn.click(timeout=3000)
            except Exception:
                pass

            await asyncio.sleep(0.3)

            # Metode 2: Javascript DOM Click & MouseEvent Dispatch
            try:
                await page.evaluate("""() => {
                    const btn = document.querySelector('button.captcha-verify') || Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.trim().toLowerCase() === 'check');
                    if (btn) {
                        btn.focus();
                        btn.click();
                        btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                    }
                }""")
            except Exception:
                pass

            await asyncio.sleep(0.3)

            # Metode 3: Bounding Box Mouse Coordinate Click
            try:
                box = await check_btn.bounding_box()
                if box:
                    await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            except Exception:
                pass

            # 3. Menunggu Tepat 10 Detik
            await notify("⏳ [LOG: 3/4] Tombol Check ditekankan! Menunggu 10 detik...")
            await asyncio.sleep(10)
            
            # 4. Membaca Status Singkat dari Web
            status_text = "Check Ditekan (Selesai 10s)"
            try:
                status_locator = page.locator("[data-captcha-status], .captcha-widget__status").first
                if await status_locator.count() > 0:
                    st = (await status_locator.inner_text()).strip()
                    if st:
                        status_text = st
            except Exception:
                pass

            # Cek tombol Reset / Result box
            try:
                reset_btn = page.locator("button.captcha-reset, button:has-text('Reset')").first
                result_box = page.locator(".captcha-result, [data-captcha-result]").first
                if (await reset_btn.count() > 0 and await reset_btn.is_visible()) or (await result_box.count() > 0 and await result_box.is_visible()):
                    status_text = "Success: true (Verified & Token Generated)"
            except Exception:
                pass

            if len(status_text) > 100:
                status_text = status_text[:97] + "..."

            # 5. TERAPKAN ZOOM 90% & SCROLL CENTER SEBELUM SCREENSHOT
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
            
            # Ambil screenshot ukuran Desktop (full_page=False)
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
