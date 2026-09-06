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
    
    Alur 2 Screenshot (Double SS):
    1. Membuka URL target & menekan tombol 'Check'.
    2. Menunggu 10 detik -> Mengambil Screenshot 1 (capskip_result_1.png).
    3. Menunggu 10 detik lagi (total 20 detik) -> Mengambil Screenshot 2 (capskip_result_2.png).
    4. Mengirim kedua gambar tersebut ke Telegram untuk membandingkan perkembangan status web.
    """
    async def notify(text: str):
        logger.info(text)
        if status_callback:
            try:
                await status_callback(text)
            except Exception:
                pass

    await notify("🌐 [LOG: 1/5] Membuka halaman CapSkip Demo...")
    
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
        ss1_path = "capskip_result_1.png"
        ss2_path = "capskip_result_2.png"
        
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
            
            # 2. Cari & Klik Tombol 'Check'
            await notify("🖱️ [LOG: 2/5] Mencari dan menekan tombol 'Check'...")
            
            check_btn = page.locator("button.captcha-verify, button:has-text('Check')").first
            await check_btn.wait_for(state="visible", timeout=15000)
            await check_btn.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            
            # Eksekusi multi-strategy click
            logger.info("Menjalankan multi-strategy click pada tombol Check...")
            try:
                await check_btn.click(timeout=3000)
            except Exception:
                pass

            await asyncio.sleep(0.3)
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
            try:
                box = await check_btn.bounding_box()
                if box:
                    await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            except Exception:
                pass

            # 3. Menunggu 10 detik pertama -> Ambil Screenshot 1
            await notify("⏳ [LOG: 3/5] Tombol Check ditekankan! Menunggu 10 detik pertama...")
            await asyncio.sleep(10)
            
            # Zoom 90%, Remove Popups, & Scroll Center
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
            await page.screenshot(path=ss1_path, full_page=False)
            logger.info(f"Screenshot 1 (10s pertama) disimpan ke: {ss1_path}")

            # 4. Menunggu 10 detik kedua (Total 20s) -> Ambil Screenshot 2
            await notify("⏳ [LOG: 4/5] Screenshot 1 diambil. Menunggu 10 detik lagi (Total 20s)...")
            await asyncio.sleep(10)
            
            # Zoom 90% & Scroll Center sekali lagi
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
            await page.screenshot(path=ss2_path, full_page=False)
            logger.info(f"Screenshot 2 (10s kedua / Total 20s) disimpan ke: {ss2_path}")

            # 5. Membaca Status Teks Singkat Akhir
            status_text = "Proses Selesai (2x Screenshot)"
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

            await notify("✨ [LOG: 5/5] Kedua screenshot berhasil diambil!")

            return {
                "success": True,
                "status_text": status_text,
                "screenshot1": ss1_path,
                "screenshot2": ss2_path
            }

        except Exception as e:
            logger.error(f"❌ Terjadi kesalahan: {e}")
            try:
                await page.screenshot(path=ss1_path, full_page=False)
            except Exception:
                pass
            return {
                "success": True,
                "status_text": f"Status: {str(e)[:80]}",
                "screenshot1": ss1_path,
                "screenshot2": None
            }
            
        finally:
            await browser.close()
            logger.info("Browser ditutup.")

if __name__ == "__main__":
    asyncio.run(run_capskip_demo(headless=True))
