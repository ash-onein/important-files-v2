from fastapi import APIRouter, HTTPException, BackgroundTasks  # type: ignore
from src.models.request_models import ArticleInput
from src.services.entity_extractor import generate_entities
from src.services.matcher import find_matches
from src.utils.text_processing import preprocess_text
from src.utils.finance_new_check_utils import is_finance_article
from src.utils.reranker import bm25_rerank_matches

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "Healthy"}

@router.post("/extract-entities/")
async def extract_entities(article: ArticleInput, background_tasks: BackgroundTasks):
    status = True
    if not is_finance_article(article.title + " " + article.content):
        status = False
        return {"status": status, "message": "Not a relevant ipo/company article"}
    else:
        clean_text = preprocess_text(article.content)
        extracted_data = await generate_entities(clean_text)

        if not extracted_data:
            raise HTTPException(status_code=500, detail="Entity extraction failed.")

        matches = find_matches(extracted_data)
        query_text = article.title + " " + article.content
        matches = bm25_rerank_matches(matches, query_text)

        # Create a set of entity names from matches (case-insensitive)
        matched_entity_names = {match["entity_name"].strip().lower() for match in matches}

        raw_entities = extracted_data.get("html_chunk_2", {})

        # Add status flag based on match
        enriched_entities = {}
        for key, values in raw_entities.items():
            normalized_key = key.strip().lower()
            is_matched = normalized_key in matched_entity_names
            enriched_entities[key] = {
                "values": values,
                "entity_matched": is_matched
            }

        return {
            "matches": matches,
            "extracted_entities": enriched_entities,
            "status": status,
        }
