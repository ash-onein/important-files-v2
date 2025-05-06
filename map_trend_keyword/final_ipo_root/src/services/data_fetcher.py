import requests  # type: ignore
import time
import yaml  # type: ignore

# Load config.yaml
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

API_URL = config["data"]["company_api_url"]
HEADERS = {
    "User-Agent": config["data"]["header"]["User-Agent"],
    "Accept": config["data"]["header"]["Accept"],
}

# Cache
company_data_cache = None
last_updated = 0
CACHE_TIMEOUT = config["data"]["cache_timeout"]

def fetch_api_data():
    """Fetch company data and cache it."""
    global company_data_cache, last_updated
    if company_data_cache and (time.time() - last_updated < CACHE_TIMEOUT):
        return company_data_cache

    print("Fetching company data from API...")
    try:
        response = requests.get(API_URL, headers=HEADERS)
        response.raise_for_status()
        company_data_cache = response.json()
        last_updated = time.time()
        return company_data_cache
    except requests.exceptions.RequestException as e:
        print(f"Error fetching API data: {e}")
        return []
