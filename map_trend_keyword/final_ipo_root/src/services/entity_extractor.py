# import requests  # type: ignore
# import yaml  # type: ignore

# # Load config.yaml
# with open("config.yaml", "r") as file:
#     config = yaml.safe_load(file)

# async def generate_entities(article_content: str):
#     url = config["entity_extraction"]["xlm_net_url"]
#     payload = {
#         "title": "",
#         "html_chunk_1": "",
#         "html_chunk_2": article_content,
#         "language": "en",
#     }
#     headers = {"Content-Type": "application/json"}

#     try:
#         response = requests.post(url, json=payload, headers=headers)
#         return response.json() if response.status_code == 200 else None
#     except Exception as e:
#         print("An error occurred:", str(e))
#         return None

import yaml  # type: ignore
import httpx  # type: ignore

# Load config.yaml ONCE globally
with open("config.yaml", "r") as file:
    CONFIG = yaml.safe_load(file)

# Create a single reusable async client
client = httpx.AsyncClient(timeout=10)

async def generate_entities(article_content: str):
    url = CONFIG["entity_extraction"]["xlm_net_url"]
    payload = {
        "title": "",
        "html_chunk_1": "",
        "html_chunk_2": article_content,
        "language": "en",
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = await client.post(url, json=payload, headers=headers)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print("An error occurred:", str(e))
        return None
