"""
Application configuration with encryption support for secrets.
"""
import os
import base64
import json
from typing import Optional, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DatabaseSettings(BaseModel):
    """Database configuration."""
    db_type: Literal["postgres", "sqlite"] = "postgres"
    host: str = "db"
    port: int = 5432
    user: str = "cxr_user"
    password: str = ""
    dbname: str = "cxr_triage"
    ssl_mode: str = "prefer"
    
    def get_connection_url(self) -> str:
        if self.db_type == "sqlite":
            return f"sqlite:///./data/{self.dbname}.db"
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
    
    def get_sync_connection_url(self) -> str:
        if self.db_type == "sqlite":
            return f"sqlite:///./data/{self.dbname}.db"
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


class AzureOpenAISettings(BaseModel):
    """Azure OpenAI configuration."""
    enabled: bool = False
    endpoint: str = ""
    deployment_name: str = ""
    api_version: str = "2024-02-15-preview"
    api_key: str = ""
    temperature: float = 0.3
    top_p: float = 0.95
    max_tokens: int = 1024
    streaming: bool = False


class ClaudeSettings(BaseModel):
    """Claude (Anthropic) configuration."""
    enabled: bool = False
    base_url: str = "https://api.anthropic.com"
    model: str = "claude-3-sonnet-20240229"
    api_key: str = ""
    temperature: float = 0.3
    top_p: float = 0.95
    max_tokens: int = 1024


class GeminiSettings(BaseModel):
    """Google Gemini configuration."""
    enabled: bool = False
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    model: str = "gemini-pro"
    api_key: str = ""
    temperature: float = 0.3
    top_p: float = 0.95
    max_output_tokens: int = 1024


class LLMSettings(BaseModel):
    """Combined LLM settings."""
    active_provider: Optional[Literal["azure_openai", "claude", "gemini"]] = None
    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)
    claude: ClaudeSettings = Field(default_factory=ClaudeSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    llm_rewrite_enabled: bool = False


class FindingThreshold(BaseModel):
    """Per-finding threshold configuration."""
    triage_threshold: float = 0.3
    strong_threshold: float = 0.7
    enabled: bool = True


class AISettings(BaseModel):
    """AI model settings."""
    # Per-finding thresholds
    pneumothorax: FindingThreshold = Field(default_factory=lambda: FindingThreshold(triage_threshold=0.25, strong_threshold=0.65))
    pleural_effusion: FindingThreshold = Field(default_factory=lambda: FindingThreshold(triage_threshold=0.3, strong_threshold=0.7))
    consolidation: FindingThreshold = Field(default_factory=lambda: FindingThreshold(triage_threshold=0.35, strong_threshold=0.7))
    cardiomegaly: FindingThreshold = Field(default_factory=lambda: FindingThreshold(triage_threshold=0.4, strong_threshold=0.75))
    edema: FindingThreshold = Field(default_factory=lambda: FindingThreshold(triage_threshold=0.35, strong_threshold=0.7))
    nodule: FindingThreshold = Field(default_factory=lambda: FindingThreshold(triage_threshold=0.3, strong_threshold=0.65))
    mass: FindingThreshold = Field(default_factory=lambda: FindingThreshold(triage_threshold=0.25, strong_threshold=0.6))
    
    # Detector settings
    detector_confidence: float = 0.25
    detector_iou: float = 0.45
    detector_max_boxes: int = 10
    
    # Calibration
    calibration_enabled: bool = True
    
    def get_threshold(self, finding_name: str) -> FindingThreshold:
        """Get threshold for a specific finding."""
        finding_map = {
            "pneumothorax": self.pneumothorax,
            "pleural_effusion": self.pleural_effusion,
            "consolidation": self.consolidation,
            "cardiomegaly": self.cardiomegaly,
            "edema": self.edema,
            "nodule": self.nodule,
            "mass": self.mass,
        }
        return finding_map.get(finding_name.lower(), FindingThreshold())


class AppSettings(BaseModel):
    """Complete application settings."""
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    ai: AISettings = Field(default_factory=AISettings)


class Settings(BaseSettings):
    """Environment-based settings."""
    # Core settings
    app_name: str = "CXR Triage System"
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production-use-strong-key")
    master_key: str = Field(default="")
    
    # Service URLs
    inference_service_url: str = "http://inference:8001"
    redis_url: str = "redis://redis:6379/0"
    orthanc_url: str = "http://orthanc:8042"
    
    # File storage
    upload_dir: str = "/app/uploads"
    models_dir: str = "/app/models"
    
    # CORS
    cors_origins: str = "*"
    
    class Config:
        env_file = ".env"
        env_prefix = "CXR_"


# Global settings instance
settings = Settings()


class SecretManager:
    """Manages encryption/decryption of secrets."""
    
    def __init__(self, master_key: str):
        if not master_key:
            master_key = settings.secret_key
        # Derive a key from the master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"cxr-triage-salt-v1",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string."""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_settings(self, app_settings: AppSettings) -> str:
        """Encrypt entire settings object."""
        json_str = app_settings.model_dump_json()
        return self.encrypt(json_str)
    
    def decrypt_settings(self, encrypted: str) -> AppSettings:
        """Decrypt settings object."""
        json_str = self.decrypt(encrypted)
        return AppSettings.model_validate_json(json_str)


# Default secret manager
def get_secret_manager() -> SecretManager:
    return SecretManager(settings.master_key or settings.secret_key)
