DEVELOPMENT_SECRET_KEY = "dev-only-insecure-secret-do-not-use-in-production"


def resolve_secret_key(app_env: str, configured_secret: str | None) -> str:
    if app_env == "production":
        if not configured_secret or len(configured_secret) < 32:
            raise RuntimeError("Production requires SECRET_KEY with at least 32 characters")
        if configured_secret.lower() in {
            DEVELOPMENT_SECRET_KEY,
            "your-secret-key-here",
            "dev-secret-key-change-in-production",
        }:
            raise RuntimeError("Production SECRET_KEY must not use a known development value")
        return configured_secret
    return configured_secret or DEVELOPMENT_SECRET_KEY


def resolve_database_url(app_env: str, configured_url: str | None) -> str:
    if app_env == "production":
        if not configured_url:
            raise RuntimeError("Production requires DATABASE_URL or SUPABASE_DATABASE_URL")
        if "dev-only-change-me" in configured_url or "yourpassword" in configured_url:
            raise RuntimeError("Production database credentials must not use a development default")
        return configured_url
    if not configured_url:
        raise RuntimeError("Development requires DATABASE_URL or TEST_DATABASE_URL")
    return configured_url