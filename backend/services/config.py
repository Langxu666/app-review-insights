from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: Optional[str] = None
    APPLE_RSS_FEED_URL: str = "https://itunes.apple.com/us/rss/customerreviews/page=1/id="

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()