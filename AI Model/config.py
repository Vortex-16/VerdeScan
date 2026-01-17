"""
Configuration management for the drone forest monitoring system.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Processing Configuration
    max_concurrent_requests: int = Field(default=5, env="MAX_CONCURRENT_REQUESTS")
    processing_timeout: int = Field(default=30, env="PROCESSING_TIMEOUT")
    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    
    # ML Model Configuration
    ml_model_path: str = Field(default="models", env="ML_MODEL_PATH")
    detection_confidence_threshold: float = Field(default=0.5, env="DETECTION_CONFIDENCE_THRESHOLD")
    classification_confidence_threshold: float = Field(default=0.7, env="CLASSIFICATION_CONFIDENCE_THRESHOLD")
    
    # External API Configuration
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-pro-vision", env="GEMINI_MODEL")
    
    # Storage Configuration
    data_dir: str = Field(default="data", env="DATA_DIR")
    static_dir: str = Field(default="static", env="STATIC_DIR")
    results_file: str = Field(default="results.json", env="RESULTS_FILE")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.data_dir,
            self.static_dir,
            self.ml_model_path,
            os.path.join(self.static_dir, "test_data"),
            os.path.join(self.static_dir, "proof_images"),
            os.path.join(self.data_dir, "patches"),
            os.path.join(self.data_dir, "cache")
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

# Global settings instance
settings = Settings()