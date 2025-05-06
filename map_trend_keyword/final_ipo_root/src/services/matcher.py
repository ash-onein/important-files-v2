# import pandas as pd  # type: ignore
# import numpy as np  # type: ignore
# from fuzzywuzzy import fuzz  # type: ignore
# from src.services.data_fetcher import fetch_api_data
# from src.utils.text_processing import normalize_name, remove_common_words
# from src.utils.location_utils import classify_location

# df = pd.DataFrame(fetch_api_data())

# # Remove entries where IndustryName is "Exchange Platform"
# df = df[df["IndustryName"] != "Exchange Platform"]

# df[["NormalizedCompanyName", "NormalizedShortName", "NormalizedTickerName"]] = df[
#     ["CompanyName", "ShortCompanyName", "TickerName"]
# ].map(normalize_name)

# def find_matches(json_data):
#     if not json_data or "html_chunk_2" not in json_data:
#         return []

#     extracted_entities = list(json_data["html_chunk_2"].keys())
#     matches = []
#     seen_company_codes = set()

#     df["CleanCompanyName"] = df["NormalizedCompanyName"].apply(remove_common_words)
#     df["CleanCompanyWords"] = df["CleanCompanyName"].str.split().apply(set)

#     for entity_name in extracted_entities:
#         name = remove_common_words(normalize_name(entity_name))
#         name_words = set(name.split())

#         # **Check if entity name is a place and apply penalty only if words < 3**
#         place_penalty = (
#             -30 if classify_location(name) == "True" and len(name.split()) < 3 else 0
#         )

#         # **Handle 'InvIT' Specific Cases**
#         if name == "invit":
#             invit_penalty = -30  # Strong penalty if "invit" exists alone
#         elif "invit" in name and len(name.split()) > 1:
#             invit_penalty = 10  # Small boost if "invit" is part of a longer name
#         else:
#             invit_penalty = 0  # No impact if "invit" is not involved

#         # Compute fuzzy scores using vectorized operations
#         scores = np.maximum(
#             df["CleanCompanyName"].apply(lambda x: fuzz.ratio(name, x) if x else 0),
#             np.maximum(
#                 df["NormalizedShortName"].apply(
#                     lambda x: fuzz.ratio(name, x) if x else 0
#                 ),
#                 df["NormalizedTickerName"].apply(
#                     lambda x: fuzz.ratio(name, x) if x else 0
#                 ),
#             ),
#         )

#         # Boost scores using vectorized conditions
#         boost = (
#             (df["CleanCompanyName"].str.contains(name, na=False))
#             | (df["NormalizedShortName"].str.contains(name, na=False))
#             | (df["NormalizedTickerName"].str.contains(name, na=False))
#         ) * 20

#         exact_match_boost = (
#             (df["CleanCompanyName"] == name) & (df["NormalizedTickerName"] == name)
#         ) * 30

#         partial_ticker_boost = (
#             df["NormalizedTickerName"].apply(lambda x: fuzz.partial_ratio(name, x) > 85)
#         ) * 15

#         core_word_penalty = (
#             ~df["CleanCompanyWords"].apply(lambda x: bool(name_words & x))
#         ) * -10

#         df["Score"] = (
#             scores
#             + boost
#             + exact_match_boost
#             + partial_ticker_boost
#             + core_word_penalty
#             + place_penalty
#             + invit_penalty
#         )

#         # Adjust threshold for short entity names
#         score_threshold = 106 if len(name) > 3 else 90

#         # Select the best match
#         best_row = df.loc[df["Score"] >= score_threshold].nlargest(1, "Score")

#         if not best_row.empty:
#             best_match = best_row.iloc[0]
#             company_code = best_match["CompanyCode"]

#             if company_code not in seen_company_codes:
#                 seen_company_codes.add(company_code)
#                 matches.append(
#                     {
#                         "entity_name": entity_name,
#                         "matched_name": str(best_match["CompanyName"]),
#                         "company_code": str(company_code),
#                         "ticker_name": str(best_match["TickerName"]),
#                         "match_score": int(
#                             best_match["Score"]
#                         ),  # Convert NumPy int64 to Python int
#                     }
#                 )

#     return matches

# --------------------code under 2s--------------------------------------------
import pandas as pd
import numpy as np
from rapidfuzz import fuzz, process
from src.services.data_fetcher import fetch_api_data
from src.utils.text_processing import normalize_name, remove_common_words
from src.utils.location_utils import classify_location

# Fetch the data
df = pd.DataFrame(fetch_api_data())

# Remove entries where IndustryName is "Exchange Platform"
df = df[df["IndustryName"] != "Exchange Platform"]

# Normalize columns just once
df[["NormalizedCompanyName", "NormalizedShortName", "NormalizedTickerName"]] = df[
    ["CompanyName", "ShortCompanyName", "TickerName"]
].map(normalize_name)

# Precompute clean names and sets
df["CleanCompanyName"] = df["NormalizedCompanyName"].apply(remove_common_words)
df["CleanCompanyWords"] = df["CleanCompanyName"].str.split().apply(set)

# Extract arrays once, FORCE type to string
clean_company_names = np.array(df["CleanCompanyName"].fillna("").astype(str).values, dtype='U')
normalized_short_names = np.array(df["NormalizedShortName"].fillna("").astype(str).values, dtype='U')
normalized_ticker_names = np.array(df["NormalizedTickerName"].fillna("").astype(str).values, dtype='U')
clean_company_words = df["CleanCompanyWords"].values

# Precompute similarities for all company names once
def precompute_similarities(names):
    return {
        'clean': process.cdist(names, clean_company_names, scorer=fuzz.QRatio),
        'short': process.cdist(names, normalized_short_names, scorer=fuzz.QRatio),
        'ticker': process.cdist(names, normalized_ticker_names, scorer=fuzz.QRatio),
        'partial_ticker': process.cdist(names, normalized_ticker_names, scorer=fuzz.partial_ratio),
    }

def find_matches(json_data):
    if not json_data or "html_chunk_2" not in json_data:
        return []

    extracted_entities = list(json_data["html_chunk_2"].keys())
    matches = []
    seen_company_codes = set()

    # Precompute similarities for the entity names
    entity_names = [remove_common_words(normalize_name(entity)) for entity in extracted_entities]
    similarities = precompute_similarities(entity_names)

    # Convert lists to numpy arrays for faster access
    clean_similarities = similarities['clean']
    short_similarities = similarities['short']
    ticker_similarities = similarities['ticker']
    partial_ticker_similarities = similarities['partial_ticker']

    # Vectorized approach to compute the scores
    for idx, entity_name in enumerate(extracted_entities):
        name = entity_names[idx]
        name_words = set(name.split())

        # Place and invit penalties vectorized
        place_penalty = -30 if classify_location(name) == "True" and len(name_words) < 3 else 0
        invit_penalty = -30 if name == "invit" else 10 if "invit" in name and len(name_words) > 1 else 0

        # Compute the similarity scores and penalties
        scores_clean = clean_similarities[idx]
        scores_short = short_similarities[idx]
        scores_ticker = ticker_similarities[idx]

        # Use max of the 3 similarity matrices
        scores = np.maximum.reduce([scores_clean, scores_short, scores_ticker])

        # Boost for substring matches
        boost = (
            np.char.find(clean_company_names, name) >= 0
        ) | (
            np.char.find(normalized_short_names, name) >= 0
        ) | (
            np.char.find(normalized_ticker_names, name) >= 0
        )
        boost = boost.astype(int) * 20

        # Exact match boost
        exact_match_boost = (
            (clean_company_names == name) & (normalized_ticker_names == name)
        ) * 30

        # Partial ticker boost
        partial_ticker_boost = (partial_ticker_similarities[idx] > 85) * 15

        # Core word penalty
        core_word_penalty = np.array([
            -10 if not (name_words & words) else 0
            for words in clean_company_words
        ])

        # Total score calculation
        total_score = (
            scores
            + boost
            + exact_match_boost
            + partial_ticker_boost
            + core_word_penalty
            + place_penalty
            + invit_penalty
        )

        # Threshold for determining a valid match
        score_threshold = 104 if len(name) > 3 else 90
        best_idx = np.where(total_score >= score_threshold)[0]

        # Collect the best matches
        if best_idx.size > 0:
            best_match_idx = best_idx[np.argmax(total_score[best_idx])]
            best_match_row = df.iloc[best_match_idx]
            company_code = best_match_row["CompanyCode"]

            if company_code not in seen_company_codes:
                seen_company_codes.add(company_code)
                matches.append(
                    {
                        "entity_name": entity_name,
                        "matched_name": str(best_match_row["CompanyName"]),
                        "company_code": str(company_code),
                        "ticker_name": str(best_match_row["TickerName"]),
                        "match_score": int(total_score[best_match_idx]),
                    }
                )

    return matches
