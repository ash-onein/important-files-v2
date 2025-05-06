import pgeocode  # type: ignore
import pycountry  # type: ignore
import pandas as pd  # type:ignore

nomi_in = pgeocode.Nominatim("IN")

def is_country(name):
    """Check if a name is a country."""
    try:
        return pycountry.countries.lookup(name) is not None
    except LookupError:
        return False

def classify_location(name):
    """Classify a name as a City, State, or Country."""
    name = name.strip().title()
    if is_country(name):
        return "True"

    india_result = nomi_in.query_location(name)
    if not india_result.empty and pd.notna(india_result.iloc[0]["state_name"]):
        return "True"

    return "False"
