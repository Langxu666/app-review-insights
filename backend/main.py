import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import router as api_router

load_dotenv()

app = FastAPI(title="App Review Insights API", version="1.0.0")

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def read_root():
    return {"message": "App Review Insights API"}