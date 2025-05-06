import asyncio
from playwright.async_api import async_playwright # type: ignore

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        await page.goto("https://trends.google.com/trending?geo=IN&hl=en-US&status=active")

        # Click the correct "Export" button
        await page.get_by_role("button", name="Export   ▾").click()

        # Wait for and click "CSV" in the dropdown
        async with page.expect_download() as download_info:
            await page.get_by_role("menuitem", name="CSV").click()
        download = await download_info.value
        await download.save_as("trending.csv")

        print("Downloaded to:", download.path())

asyncio.run(run())

if __name__ == "__main__":
    asyncio.run(run())
    print("Script completed.")