import joblib  # type: ignore
from src.utils.text_processing import preprocess_text

def is_finance_article(text):
    # load and use the model:
    loaded_pipeline = joblib.load("./src/models/finance_news_classifier_v2.joblib")
    return loaded_pipeline.predict([text])
