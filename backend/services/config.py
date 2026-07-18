from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    APPLE_RSS_FEED_URL: str = "https://itunes.apple.com/us/rss/customerreviews/page=1/id="

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()