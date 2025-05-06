import re

def preprocess_text(input_text: str, max_length: int = 10000) -> str:
    input_text = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", input_text)
    input_text = re.sub(
        r"[^\w\s.,()]", " ", input_text
    )  # Replace all special characters except .,() with space
    input_text = re.sub(r"\s+", " ", input_text).strip()
    input_text = input_text.encode("utf-8", "ignore").decode("utf-8")
    return (
        input_text[:max_length] + "..." if len(input_text) > max_length else input_text
    )

def normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\s]", "", str(name)).lower().strip()

def remove_common_words(text: str) -> str:
    common_words = {"limited", "ltd", "corp", "company"}
    return " ".join([word for word in text.split() if word.lower() not in common_words])
