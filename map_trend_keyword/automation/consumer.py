import json
import logging
import threading
import time
from datetime import datetime,date
from kafka import KafkaConsumer  # type: ignore
import gspread  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow # type: ignore
import schedule  # type: ignore

# Kafka configuration
KAFKA_TOPIC = "trend_capture"
KAFKA_BROKER = "localhost:9092"

# Google Sheets Configuration
GOOGLE_SHEET_NAME = "New Trending"
CREDENTIALS_FILE = "/home/oi.temp-aswathi/map_trend_keyword/client_secret.json"

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def connect_to_gsheet():
    """Authenticate and return the worksheet."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.metadata.readonly"
    ]
    # Authenticate using the OAuth client credentials
    flow = InstalledAppFlow.from_client_secrets_file("/home/oi.temp-aswathi/map_trend_keyword/client_secret.json", scopes=scopes)
    creds = flow.run_local_server(port=0)

    # Connect to Google Sheets
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME).worksheet("auto_extract")

def is_today(publish_date_str):
    """Check if the given date string is today."""
    try:
        pub_date = datetime.strptime(publish_date_str, "%Y-%m-%d %H:%M:%S").date()
        return pub_date == date.today()
    except Exception:
        return False

def create_header_if_needed(sheet):
    """Create the header row if the sheet is empty or missing headers."""
    expected_headers = ["ArticleID", "WebURL", "CategoryName", "Domain", "Title", "Content", "Publish_date", "Language"]
    rows = sheet.get_all_values()

    if not rows or rows[0] != expected_headers:
        sheet.clear()  # Clear the sheet first to avoid duplication
        sheet.append_row(expected_headers)
        logging.info("✅ Created header row in Google Sheets.")

def remove_old_rows(sheet):
    """Remove rows older than today."""
    rows = sheet.get_all_values()
    if len(rows) <= 1:
        return  # Only header or empty sheet

    headers = rows[0]
    
    try:
        date_col_index = headers.index("Publish_date")
    except ValueError:
        logging.warning("⚠️ 'Publish_date' column not found in headers.")
        return

    to_delete = []

    for i, row in enumerate(rows[1:], start=2):  # 1-indexed; skip header
        if len(row) <= date_col_index:
            continue  # Skip rows without a publish_date

        pub_date_str = row[date_col_index].strip()
        try:
            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d %H:%M:%S").date()
            if pub_date != date.today():
                to_delete.append(i)
        except Exception as e:
            logging.warning(f"⚠️ Skipping malformed date in row {i}: {pub_date_str} ({e})")
            continue

    # Delete from bottom to top to avoid index shifting
    for i in reversed(to_delete):
        sheet.delete_rows(i)

    if to_delete:
        logging.info(f"🗑️ Removed {len(to_delete)} outdated rows from Google Sheets.")
    else:
        logging.info("✅ No outdated rows found to remove.")


def kafka_consumer_job():
    """Continuously consume Kafka messages and write valid ones to Google Sheets."""
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None
    )

    sheet = connect_to_gsheet()
    create_header_if_needed(sheet)

    # Cache today's date and refresh every hour
    current_day = date.today()

    # Get existing IDs to prevent duplication
    existing_rows = sheet.get_all_values()
    existing_ids = set(row[0].strip() for row in existing_rows[1:] if row)

    logging.info("📥 Kafka consumer is now listening for messages...")

    while True:
        for message in consumer:
            try:
                article = message.value
                if not article:
                    continue

                # Refresh existing ID cache and date if day changes
                if date.today() != current_day:
                    current_day = date.today()
                    existing_rows = sheet.get_all_values()
                    existing_ids = set(row[0].strip() for row in existing_rows[1:] if row)
                    logging.info("🔁 Refreshed cache for new day")

                article_id = str(article.get("ArticleID", "")).strip()
                publish_date = article.get("publish_date", "").strip()

                # Skip if not today's article or duplicate
                if not is_today(publish_date):
                    logging.info(f"⏭️ Skipped old article {article_id} ({publish_date})")
                    continue
                if article_id in existing_ids:
                    continue

                row = [
                    article_id,
                    article.get("web_url", "").strip(),
                    article.get("category", "").strip(),
                    article.get("domain", "").strip(),
                    article.get("title", "").strip(),
                    article.get("content", "").strip(),
                    publish_date,
                    article.get("language", "").strip()
                ]

                sheet.append_row(row)
                existing_ids.add(article_id)
                logging.info(f"✅ Appended article {article_id}")

                time.sleep(1)  # To avoid hitting Sheets rate limits

            except Exception as e:
                logging.error(f"❌ Error processing Kafka message: {e}")


def cleanup_job():
    """Cleanup job that removes rows older than today."""
    sheet = connect_to_gsheet()
    remove_old_rows(sheet)

def run_scheduler():
    """Run the scheduler every 1 hour to clean up old data."""
    schedule.every(1).hours.do(cleanup_job)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute for scheduled tasks

def main():
    """Main function to run Kafka consumer and scheduler."""
    logging.info("🔄 Starting Kafka consumer to write to Google Sheets...")

    # Run the Kafka consumer in a separate thread
    consumer_thread = threading.Thread(target=kafka_consumer_job)
    consumer_thread.start()

    time.sleep(3)  # Give some time for the consumer to start
    
    # Run the scheduler for cleanup jobs in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    # Keep the main thread running to allow continuous operation
    while True:
        time.sleep(3600)  # Sleep for 1 hour before checking again

if __name__ == "__main__":
    main()