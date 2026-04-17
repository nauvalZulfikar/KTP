from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KTP_", extra="ignore")

    database_url: str = f"sqlite:///{BACKEND_DIR / 'ktp.db'}"
    excel_path: Path = PROJECT_ROOT / "Product Details_v1.xlsx"

    work_start_hour: int = 9
    work_end_hour: int = 17
    weekend_days: list[int] = [5, 6]


settings = Settings()
