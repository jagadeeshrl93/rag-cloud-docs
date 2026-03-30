from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    chroma_persist_dir: str = ".chroma"
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()