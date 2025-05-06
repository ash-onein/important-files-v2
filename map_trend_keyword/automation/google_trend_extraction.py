import asyncio
import csv
import time
from datetime import datetime
import schedule # type: ignore

import gspread # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow # type: ignore
from playwright.async_api import async_playwright # type: ignore

GOOGLE_SHEET_NAME = "New Trending"  # Make sure this matches your actual sheet name

def connect_to_gsheet():
    """Authenticate and return the google_rss worksheet."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.metadata.readonly"
    ]
    flow = InstalledAppFlow.from_client_secrets_file(
        "/home/oi.temp-aswathi/map_trend_keyword/client_secret.json",
        scopes=scopes
    )
    creds = flow.run_local_server(port=0)
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME).worksheet("google_extract")

async def download_trending_csv():
    """Download the trending CSV file from Google Trends."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        await page.goto("https://trends.google.com/trending?geo=IN&hl=en-US&status=active")

        await page.get_by_role("button", name="Export   ▾").click()
        async with page.expect_download() as download_info:
            await page.get_by_role("menuitem", name="CSV").click()
        download = await download_info.value
        path = "trending.csv"
        await download.save_as(path)
        await browser.close()
        return path

def overwrite_worksheet_with_csv(csv_file):
    """Clear existing data and write new CSV content to worksheet."""
    ws = connect_to_gsheet()

    # Clear the worksheet first
    ws.clear()

    # Load and write new CSV data
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        data = list(reader)

    ws.update("A1", data)
    print(f"[{datetime.now()}] Overwrote google_rss worksheet with latest data.")

async def main_job():
    try:
        csv_path = await download_trending_csv()
        overwrite_worksheet_with_csv(csv_path)
    except Exception as e:
        print(f"Error during job: {e}")

def job():
    print(f"[{datetime.now()}] Running scheduled job...")
    asyncio.run(main_job())

schedule.every().hour.do(job)

if __name__ == "__main__":
    job()  # Optional: run immediately on startup
    print("Scheduler is active. Running job every hour.")
    while True:
        schedule.run_pending()
        time.sleep(60)
