from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=("model_",),
    )

    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "novelforge"
    use_mock_llm: bool = False
    settings_encryption_key: str = ""
    settings_key_file: str = ""
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    local_access_token: str = ""
    publication_export_directory: str = "./exports"
    backup_directory: str = ""
    support_bundle_directory: str = ""
    backup_retention_count: int = 10
    minimum_free_space_mb: int = 512

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [value.strip() for value in self.trusted_hosts.split(",") if value.strip()]
    
settings = Settings()
