import os
import asyncio
from playwright.async_api import async_playwright

async def refresh_cookies():
    """
    Обновляет куки через Playwright (логин в YouTube)
    Использовать только если ytc не сработал!
    """
    email = os.getenv("GOOGLE_EMAIL")
    password = os.getenv("GOOGLE_PASSWORD")
    
    if not email or not password:
        print("❌ GOOGLE_EMAIL или GOOGLE_PASSWORD не заданы!")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Логинимся в Google
            await page.goto("https://accounts.google.com/signin")
            await page.fill('input[type="email"]', email)
            await page.click('button:has-text("Далее")')
            await page.wait_for_load_state("networkidle")
            await page.fill('input[type="password"]', password)
            await page.click('button:has-text("Далее")')
            await page.wait_for_load_state("networkidle")
            
            # Переходим на YouTube
            await page.goto("https://www.youtube.com")
            await page.wait_for_load_state("networkidle")
            
            # Сохраняем куки
            cookies = await page.context.cookies()
            with open("DeepLegs", "w") as f:
                f.write("# Netscape HTTP Cookie File\n")
                for cookie in cookies:
                    if "youtube" in cookie.get("domain", ""):
                        f.write(f"{cookie['domain']}\tTRUE\t{cookie['path']}\t{cookie.get('secure', 'FALSE')}\t{cookie.get('expires', 0)}\t{cookie['name']}\t{cookie['value']}\n")
            
            print("✅ Куки обновлены через Playwright!")
            
        except Exception as e:
            print(f"❌ Ошибка обновления кук: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(refresh_cookies())
