# Financial Article Entity Extraction

## Overview
This project is designed to **identify company names** present in a given financial article. It first determines if the article is relevant to trade. If the article is relevant, it will extract and suggest the company names mentioned; otherwise, it will return **"Not a relevant financial article."**

The project uses:
- **XLM-Roberta-NER Model** (Hosted on [TorchServe endpoint](http://10.90.128.83:8080/predictions/xlm-net/1.0)) for entity extraction.
- **A company database** (from [GoodReturns](https://www.goodreturns.in/src/cms_api.php?data=company-list)) for validation.
- **FastAPI** as the backend framework to serve the results.

---

## Features
- Classifies articles as **relevant or irrelevant**.
- Extracts company names from relevant articles using Naive Bayes Classifier model trained on 5970 datapoints.
- Cross-checks extracted names with the [**GoodReturns company list**](https://www.goodreturns.in/src/cms_api.php?data=company-list).
- Uses [**TorchServe**](http://10.90.128.83:8080/predictions/xlm-net/1.0) for xlm-roberta-ner-prod DH model hosting.
- API-based **FastAPI** backend for easy integration.

---

## Project Structure

```
project_root/
│── src/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API endpoints for classification and entity extraction
│   ├── services/
│   │   ├── __init__.py
│   │   ├── data_fetcher.py  # Fetches company list from GoodReturns API
│   │   ├── entity_extractor.py # Extracts entities using XLM-Roberta
│   │   └── matcher.py       # Matches extracted entities with GoodReturns list
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── text_processing.py  # Cleans and processes article text
│   │   ├── location_utils.py   # Helper functions for location-based checks
│   │   ├── reranker.py   # Helper functions for reranking the final output based on the context
│   │   └── finance_news_check_utils.py # Filters relevant finance news
│   ├── models/
│   │   ├── __init__.py
│   │   ├── finance_news_classifier_v2.joblib # Naive Bayes Classifier model
│   │   └── request_models.py # Defines request/response data models
│── main.py          # Entry point for FastAPI server
│── requirements.txt # Python dependencies
│── config.yaml      # For storing constant values
│── setup_and_run.sh # Shell script to setup and run the application
│── .dockerignore    # Files to be ignored while running docker container
│── Dockerfile       # Docker configuration for containerized deployment
│── docker-compose.yml # Configuration for Docker Compose setup
│── README.md        # Project documentation
```

---

## 🛠️ Setup & Installation

### **1️⃣ Prerequisites**
- Python **3.10+**
- Docker & Docker Compose
- FastAPI
- **cURL** (for testing API endpoints)

### **2️⃣ Clone the Repository**
#### **Clone the repository and change the base directory to IPO_root**
```sh
git clone <repository-url>
cd IPO_root
```

### **3️⃣ Run Locally (Without Docker)**

#### **Run the setup_and_run.sh file to start TorchServe and FastAPI**
```sh
bash setup_and_run.sh
```

---

## API Endpoints

### **For Irrelevant Articles**
**Endpoint:** `POST https://aimloi.dailyhunt.in/company-names`

#### **cURL Request**
```sh
curl -X POST "https://aimloi.dailyhunt.in/company-names" \
     -H "Content-Type: application/json" \
     -d '{
         "title": "India CPI Inflation At 7-Month Low",
         "content": "India consumer price index (CPI) inflation cooled to 3.6%..."
     }'
```

#### **Response**
```json
{
    "status" : false,
    "message": "Not a relevant ipo/company article"
}
```

---

### **For Relevant Articles**
**Endpoint:** `POST https://aimloi.dailyhunt.in/company-names`

#### **cURL Request**
```sh
curl -X POST "https://aimloi.dailyhunt.in/company-names" \
     -H "Content-Type: application/json" \
     -d '{
         "title": "Tata Steel, Hindalco, JSW Steel Buzzing: Why Metal Stocks Are Outperforming?",
         "content": "Driven by China recovery, metal stocks, Tata Steel, Hindalco, JSW Steel, have outperformed Nifty-50..."
     }'
```

#### **Response**
```json
{
    "matches": [
        {
            "entity_name": "jsw steel",
            "matched_name": "JSW Steel Ltd.",
            "company_code": "15530059",
            "ticker_name": "JSW Steel",
            "match_score": 165,
            "bm25_score": 1.0544565628197058
        },
        {
            "entity_name": "tata steel",
            "matched_name": "Tata Steel Ltd.",
            "company_code": "15510001",
            "ticker_name": "Tata Steel",
            "match_score": 165,
            "bm25_score": 1.0544565628197058
        },
        {
            "entity_name": "hindalco",
            "matched_name": "Hindalco Industries Ltd.",
            "company_code": "15040001",
            "ticker_name": "Hindalco",
            "match_score": 135,
            "bm25_score": 0.0
        }
    ],
    "extracted_entities": {
        "china": {
            "values": [
                "china"
            ],
            "entity_matched": false
        },
        "hindalco": {
            "values": [
                "hindalco"
            ],
            "entity_matched": true
        },
        "nifty 50": {
            "values": [
                "nifty 50"
            ],
            "entity_matched": false
        },
        "jsw steel": {
            "values": [
                "jsw steel"
            ],
            "entity_matched": true
        },
        "tata steel": {
            "values": [
                "tata steel"
            ],
            "entity_matched": true
        }
    },
    "status": true
}
```

---

## Health Check

To ensure that the services are running correctly, you can perform health checks on both TorchServe and FastAPI.

### **TorchServe:**
**Endpoint:** `GET http://10.90.128.83:8080/ping`

**Expected Response:**
```json
{
    "status": "Healthy"
}
```

### **FastAPI:**
**Endpoint:** `GET https://aimloi.dailyhunt.in/ping`

**Expected Response:**
```json
{
    "status": "Healthy"
}
```

---

## 🛡️ Troubleshooting

### **Container Issues?**
If you encounter issues with Docker containers, try the following steps:

#### **Using Docker Run:**
1. **Stop and remove the running container:**
``` sh
    docker stop fastapi-ipo-app && docker rm fastapi-ipo-app
```
2. **Remove all the images:**
```sh
    docker rmi fastapi-ipo-app --force
```
3. **Rebuild and start the container:**
```sh
    docker build --memory=8g --memory-swap=16g -t fastapi-ipo-app .
    docker run -p 8002:8002 -p 8094:8094 -p 8095:8095 fastapi-ipo-app
```

#### **Using Docker Compose:**
1. **Stop and remove all containers and networks created by docker-compose:**
```sh
    docker-compose down && docker system prune -f
```
2. **Rebuild and start the containers:**
```sh
    docker-compose up --build
```

---

## 📝 License
This project is available under the **MIT License**.

💡 **For Contributions & Support, feel free to open an issue or submit a PR!** 🚀

---

## Acknowledgments
We would like to acknowledge `DailyHunt` for providing the `XLM-RoBERTa` model used in this project. This model has been instrumental in achieving high-quality results in multilingual natural language processing tasks.

For more information about the model, please refer to the [official repository](https://gitlab.dailyhunt.in/rishab.jain/xlm-roberta-ner.git).

