from playwright.sync_api import sync_playwright
import json

def scrape_shopee_with_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)

        page.wait_for_selector("title", timeout=15000)

        title = page.title()
        image = None
        price = None

        content = page.content()
        if "window.__INITIAL_STATE__" in content:
            try:
                scripts = page.query_selector_all("script")
                for script in scripts:
                    script_text = script.inner_text()
                    if "window.__INITIAL_STATE__" in script_text:
                        json_text = script_text.split("=", 1)[1].strip().rstrip(";")
                        data = json.loads(json_text)
                        item = data["product"]["item"]
                        image = item.get("images", [None])[0]
                        price = item.get("price")
                        break
            except Exception as e:
                print("⚠️ Erro ao extrair dados do JSON Shopee:", e)

        browser.close()

        return {
            "name": title,
            "image": f"https://down-id.img.susercontent.com/file/{image}" if image else None,
            "price": price
        }
