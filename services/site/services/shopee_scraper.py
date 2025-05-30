from playwright.sync_api import sync_playwright
import re

def scrape_shopee_product(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)

        # Espera carregamento de elementos essenciais
        page.wait_for_selector("div.page-product__content", timeout=15000)

        # Título
        title = page.locator("div.title--wrap").inner_text(timeout=5000)

        # Imagem (src da imagem principal)
        image = page.locator("div.product-image__main img").get_attribute("src")

        # Preço (pegando o menor valor visível como preço final)
        price_element = page.locator("div.pdp-price")
        price_text = price_element.inner_text().strip() if price_element else ""
        price_clean = re.search(r"R\$ ?\d+[\.,]?\d*", price_text)
        price = price_clean.group(0) if price_clean else "Indisponível"

        browser.close()

        return {
            "name": title,
            "image": image,
            "price": price
        }
