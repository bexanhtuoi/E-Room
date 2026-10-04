import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8005"))
    scorer_api_key: str = os.getenv("SCORER_API_KEY", "")
    embed_model_id: str = os.getenv("EMBED_MODEL_ID", "Qwen/Qwen3-Embedding-0.6B")
    wav2vec_model_id: str = os.getenv("WAV2VEC_MODEL_ID", "facebook/wav2vec2-base-960h")
    phoneme_model_id: str = os.getenv("PHONEME_MODEL_ID", "facebook/wav2vec2-xlsr-53-espeak-cv-ft")


settings = Settings()
