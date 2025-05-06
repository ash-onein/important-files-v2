import requests  # type: ignore
import logging
from bs4 import BeautifulSoup as bs  # type: ignore
import time
import html
import re
import socket
import json
from datetime import datetime, timedelta
from kafka import KafkaProducer  # type: ignore

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Kafka settings
KAFKA_TOPIC = "trend_capture"
KAFKA_BROKER = "localhost:9092"
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# RSS Feed configurations
DOMAIN_LANGUAGE_MAPPING = {
    "boldsky.com": ["Bengali", "Kannada", "Hindi", "Telugu", "Malayalam", "Tamil", "English"],
    "careerindia.com": ["Kannada", "Tamil", "Hindi", "English"],
    "drivespark.com": ["Telugu", "Hindi", "Malayalam", "Kannada", "Tamil", "English"],
    "filmibeat.com": ["Kannada", "Malayalam", "Hindi", "Tamil", "Telugu", "English"],
    "gizbot.com": ["Gujarati", "Hindi", "Telugu", "Malayalam", "Kannada", "Tamil", "English"],
    "goodreturns.in": ["Kannada", "Malayalam", "Telugu", "Hindi", "Tamil", "English"],
    "mykhel.com": ["Kannada", "Tamil", "Malayalam", "Telugu", "English"],
    "nativeplanet.com": ["Kannada", "Telugu", "Tamil", "Hindi", "Malayalam", "English"],
    "oneindia.com": ["Marathi", "Odia", "Gujarati", "Bengali", "Kannada", "Telugu", "Malayalam", "Tamil", "Hindi", "English"]
}

LANGUAGE_SUBDOMAIN_MAPPING = {
    "Bengali": "bengali",
    "Kannada": "kannada",
    "Hindi": "hindi",
    "Telugu": "telugu",
    "Malayalam": "malayalam",
    "Tamil": "tamil",
    "English": "www",
    "Marathi": "marathi",
    "Odia": "odia",
    "Gujarati": "gujarati"
}

# HTTP Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

# Store previously fetched articles to avoid duplicates
seen_articles = set()

def call_xml(lnk: str, retries: int = 3) -> bs:
    """Fetch XML data from a given link."""
    for attempt in range(retries):
        try:
            response = requests.get(lnk, headers=HEADERS, timeout=10)
            response.encoding = "utf-8"
            if response.status_code == 200:
                return bs(response.text, "xml")
            else:
                logging.error(f"Error fetching XML from {lnk}: Status Code {response.status_code}")
        except (requests.exceptions.RequestException, socket.gaierror) as e:
            logging.error(f"Error fetching XML from {lnk} (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(2)
    return None

def process_items(items, domain, language):
    """Extract article details and clean content."""
    articles = []
    for item in items:
        try:
            link = item.find("Link").text if item.find("Link") else "No Link"
            pubdate = item.find("PublishDate").text if item.find("PublishDate") else "No Publish Date"
            category_elem = item.find("CategoryName")
            category = category_elem.text.strip() if category_elem is not None and category_elem.text else "No Category"

            content_elem = call_xml(link)
            try:
                article_id = content_elem.find("ContentId").text if content_elem.find("ContentId") else "No ID"
                title = content_elem.find("Title").text if content_elem.find("Title") else "No Title"
                content = content_elem.find("Content").text if content_elem.find("Content") else "No Content"
                clean_content = re.sub(r"<.*?>|(&[^;]+;)", "", html.unescape(content)).replace('\\', " ")
                content = re.sub(r'[\s]{2,}', ' ', clean_content)
            except Exception as e:
                article_id = f"Error: {e}"

            if article_id in seen_articles:
                continue  # Skip duplicate articles
            seen_articles.add(article_id)

            articles.append({
                "publish_date": pubdate,
                "category": category,
                "web_url": link,
                "ArticleID": article_id,
                "title": title,
                "content": content,
                "domain": domain,
                "language": language
            })
        except Exception as e:
            logging.error(f"Error processing item: {e}")
    return articles

def fetch_articles(domain, language):
    """Fetch articles for a specific domain and language from the past 60 days."""
    try:
        subdomain = LANGUAGE_SUBDOMAIN_MAPPING.get(language, "www")  # Default to "www" for English
        site = f"{subdomain}.{domain}"
        page_number = 1
        articles = []
        cutoff_date = datetime.now() - timedelta(days=2)

        while True:
            main_link = f"https://rss.oneindia.com/scripts/cms/newsFeed.php?type=dh-feed&sub_type=all&site={site}&limit=30&page={page_number}"
            root = call_xml(main_link)
            
            if not root:
                logging.error(f"Failed to fetch the XML feed for domain {domain}, language {language}, page {page_number}")
                break
            
            items = root.find_all('Item')
            if not items:
                break  # Stop if no more items are found
            
            for item in items:
                pubdate = item.find("PublishDate").text if item.find("PublishDate") else "No Publish Date"
                try:
                    article_date = datetime.strptime(pubdate, "%Y-%m-%d %H:%M:%S")
                    if article_date < cutoff_date:
                        return articles  # Stop fetching if article is older than 60 days
                except ValueError:
                    logging.warning(f"Skipping article with invalid date format: {pubdate}")
                    continue
                
                articles.extend(process_items([item], domain, language))
            
            page_number += 1  # Move to the next page
            logging.info(f"Fetched page {page_number} for domain {domain}, language {language}")
            time.sleep(1)  # Avoid overwhelming the server
        
        return articles
    except Exception as e:
        logging.error(f"Error fetching data for domain {domain}, language {language}: {e}")
    return []

def kafka_produce(articles):
    """Send articles to Kafka."""
    for article in articles:
        producer.send(KAFKA_TOPIC, article)
        logging.info(f"Sent to Kafka: {article['domain']} -{article['language']}- {article['ArticleID']}")

def main():
    """Fetch articles for all domains and languages and send them to Kafka."""
    for domain, languages in DOMAIN_LANGUAGE_MAPPING.items():
        for language in languages:
            articles = fetch_articles(domain, language)
            if articles:
                kafka_produce(articles)


if __name__ == "__main__":
    while True:
        main()
        time.sleep(300)  # Run every 5 minutes