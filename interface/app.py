from flask import Flask, render_template, request, jsonify # type: ignore
from pymongo import MongoClient # type: ignore
import os
from dotenv import load_dotenv # type: ignore
import requests # type: ignore
from bs4 import BeautifulSoup as bs # type: ignore
import math
from rapidfuzz import fuzz, process # type: ignore
from collections import defaultdict
import re

load_dotenv()

app = Flask(__name__)

# Connect to MongoDB
mongo_user = os.getenv('mongo_user')
mongo_password = os.getenv('mongo_password')
mongo_host = os.getenv('mongo_host')
mongo_port = os.getenv('mongo_port')
mongo_db = os.getenv('mongo_db')

client = MongoClient(f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db}")
db = client[mongo_db]

@app.route('/')
def search_page():
    return render_template('search.html')

@app.route('/results')
def results_page():
    return render_template('results.html')

@app.route('/search_names', methods=['GET'])
def search_names():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    matches = db.qid_level_tab.find(
        {"$or": [
            {"data.FB_name": {"$regex": f"^{query}", "$options": "i"}},  # Match from start
            {"data.aka": {"$regex": f"^{query}", "$options": "i"}},  # Match from start
            {"data.OI_name": {"$regex": f"^{query}", "$options": "i"}}
        ]},
        {"data.FB_name": 1, "data.OI_name": 1, "_id": 0}
    )
    
    names = set()
    for doc in matches:
        if "data" in doc:
            if "FB_name" in doc["data"]:
                names.add(doc["data"]["FB_name"])
            if "OI_name" in doc["data"]:
                names.add(doc["data"]["OI_name"])
    
    return jsonify(list(names))

def sanitize_data(data):
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(i) for i in data]
    elif data is None or (isinstance(data, float) and math.isnan(data)):
        return ""
    return data
    
def normalize(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)     # collapse multiple spaces
    text = re.sub(r'(.)\1+', r'\1', text)  # reduce repeated letters: rahmaan → rahman
    return text.strip()


@app.route('/get_articles', methods=['GET'])
def get_articles():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({"error": "No name provided"}), 400

    # Step 1: Direct match lookup
    qid_doc = db.qid_level_tab.find_one(
        {"$or": [{"data.FB_name": name}, {"data.OI_name": name}, {"data.aka": name}]}
    )

    if not qid_doc:
        # Step 2: Build name map (for reverse mapping aka → FB/OI)
        all_names_cursor = db.qid_level_tab.find({}, {"data.FB_name": 1, "data.OI_name": 1, "data.aka": 1})
        
        name_map = defaultdict(set)
        normalized_name_map = {}  # key: normalized name, value: original name(s)

        for doc in all_names_cursor:
            fb = doc["data"].get("FB_name")
            oi = doc["data"].get("OI_name")
            akas = doc["data"].get("aka", [])

            if isinstance(akas, str):
                akas = [akas]

            canonical_name = fb or oi
            for n in filter(None, [fb, oi] + akas):
                name_map[n].add(canonical_name)
                normalized = normalize(n)
                normalized_name_map[normalized] = n
        
       
        normalized_input = normalize(name)
        matches = process.extract(
            normalized_input,
            list(normalized_name_map.keys()),
            scorer=fuzz.token_set_ratio,
            limit=5
        )
        
        suggestions = []
        for norm_key, score, _ in matches:
            if score >= 60:
                original_name = normalized_name_map[norm_key]
                for canonical in name_map[original_name]:
                    if canonical not in suggestions:
                        suggestions.append(canonical)
            if len(suggestions) >= 3:
                break

        if suggestions:
            return jsonify({
                "error": "No exact match found",
                "did_you_mean": suggestions
            }), 200
        else:
            return jsonify({"error": "No match found"}), 404

    # Step 4: Get QID
    qid = qid_doc["_id"]

    # Step 5: Fetch articles
    articles = list(db.item_level_tab.find(
        {"qid": qid},
        {"_id": 1, "domain": 1, "publish_date": 1, "article_url": 1}
    ))

    # Step 6: Get profile data
    qid_details = db.qid_level_tab.find_one(
        {"_id": qid},
        {"data.FB_id": 0, "data.OI_id": 0, "_id": 0}
    )

    qid_details = sanitize_data(qid_details)

    # Step 7: Parse article URLs
    for article in articles:
        if "article_url" in article:
            try:
                response = requests.get(article["article_url"])
                response.encoding = "utf-8"
                if response.status_code == 200:
                    soup = bs(response.text, "xml")
                    article["article_url"] = soup.find("WebUrl").text if soup.find("WebUrl") else "No WebLink found"
                    article["title"] = soup.find("Title").text if soup.find("Title") else "No Title found"
            except Exception as e:
                print(f"Error fetching article: {e}")

    return jsonify({"qid_details": qid_details, "articles": articles})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# -------------------------------------------------------