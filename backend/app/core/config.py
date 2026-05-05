from pydantic import model_validator
from pydantic_settings import BaseSettings

_DEFAULT_JWT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    # DB
    DATABASE_URL: str = "sqlite:///./earth_canvas.db"

    # Deployment environment — used to gate dev-only fallbacks.
    ENV: str = "development"

    # JWT
    # JWT_SECRET_KEY is the canonical name. SECRET_KEY is kept as a backward-compat
    # alias so older deployments whose env already sets SECRET_KEY don't silently
    # fall back to the insecure default below. Resolution order: JWT_SECRET_KEY > SECRET_KEY > default.
    JWT_SECRET_KEY: str = _DEFAULT_JWT_SECRET
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7일

    # OAuth — Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # OAuth — Kakao
    KAKAO_CLIENT_ID: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = "http://localhost:8000/api/auth/kakao/callback"

    # Dev login (MVP only). Issues a JWT for any email — must be OFF in prod.
    # Default False so a missing env var can never accidentally enable it in prod.
    # Local dev opts in via .env (see .env.example).
    ALLOW_DEV_LOGIN: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def _resolve_jwt_secret(self):
        # Backward compat: if JWT_SECRET_KEY is still the placeholder but legacy
        # SECRET_KEY was provided, promote it. This prevents the silent fallback
        # to the insecure default when someone upgrades without renaming env vars.
        if self.JWT_SECRET_KEY == _DEFAULT_JWT_SECRET and self.SECRET_KEY:
            object.__setattr__(self, "JWT_SECRET_KEY", self.SECRET_KEY)

        # In production, refuse to start with the known-insecure default secret.
        if (
            self.ENV.lower() == "production"
            and self.JWT_SECRET_KEY == _DEFAULT_JWT_SECRET
        ):
            raise ValueError(
                "JWT_SECRET_KEY (or legacy SECRET_KEY) must be set in production — "
                "refusing to run with the default placeholder secret."
            )
        return self


settings = Settings()
