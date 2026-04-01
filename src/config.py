from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str = "your_bot_token_from_botfather"
    ADMIN_IDS: str = ""

    # AI Providers
    GROQ_API_KEY: str = ""       
    GROK_API_KEY: str = ""    
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_URL: str = ""      
    OLLAMA_MODEL: str = "qwen2.5:1.5b"
    LIBERTAI_API_KEY: str = ""    
    CHAINGPT_API_KEY: str = ""   

    # TON Blockchain
    TON_API_KEY: str = ""
    TON_WALLET_ADDRESS: str = ""
    TON_TESTNET: bool = True
    DEPOSIT_AMOUNT_TON: float = 2.0

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///data/clawbot.db"

    # Rate limiting / permissions
    MAX_BOOKINGS_PER_USER: int = 3
    MAX_PARTY_SIZE: int = 20
    BOOKING_WINDOW_DAYS: int = 30
    REQUIRE_DEPOSIT: bool = False 

    # Optional
    REDIS_DSN: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "DEBUG"

    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    @property
    def ton_api_base_url(self) -> str:
        if self.TON_TESTNET:
            return "https://testnet.toncenter.com/api/v2"
        return "https://toncenter.com/api/v2"


settings = Settings()
