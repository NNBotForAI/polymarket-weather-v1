"""Application configuration via environment / .env."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "polymarket-weather-v1"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/polymarket_weather"

    # Polymarket
    polymarket_api_base: str = "https://gamma-api.polymarket.com"

    # Weather
    weather_api_key: str = ""
    weather_api_base: str = "https://api.openweathermap.org/data/2.5"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
