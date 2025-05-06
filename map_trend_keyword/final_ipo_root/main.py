import uvicorn  # type: ignore
from fastapi import FastAPI  # type: ignore
from fastapi.responses import ORJSONResponse  # type: ignore
from src.api.routes import router
import yaml  # type: ignore

app = FastAPI(default_response_class=ORJSONResponse)
app.include_router(router)

# Load config.yaml if available
try:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
except FileNotFoundError:
    config = {"api": {"host": "0.0.0.0", "port": 8002}}

if __name__ == "__main__":
    uvicorn.run(
        "main:app", host=config["api"]["host"], port=config["api"]["port"], reload=True
    )
