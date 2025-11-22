# Common utilities - Secrets Management
import os
from typing import Dict, Optional
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class TradingSecrets:
    """Trading system secrets"""
    
    # Database
    database_url: str
    
    # JWT
    jwt_secret: str
    jwt_expiration_hours: int
    
    # TradingView
    tradingview_webhook_secret: str
    
    # API Keys
    api_key: str
    
    # MT5 Credentials
    mt5_login: str
    mt5_password: str
    mt5_server: str
    
    # Redis
    redis_url: str
    
    # S3/MinIO (for model storage)
    s3_endpoint: Optional[str]
    s3_access_key: Optional[str]
    s3_secret_key: Optional[str]
    s3_bucket: str
    
    # Monitoring
    prometheus_enabled: bool
    alert_webhook_url: Optional[str]  # Slack, PagerDuty, etc.


class SecretsManager:
    """Centralized secrets management"""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize secrets manager
        
        Args:
            env_file: Path to .env file (optional)
        """
        self.env_file = env_file
        if env_file and Path(env_file).exists():
            self._load_env_file(env_file)
    
    def _load_env_file(self, env_file: str):
        """Load environment variables from file"""
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    def get_secrets(self) -> TradingSecrets:
        """
        Load all secrets from environment variables
        
        Returns:
            TradingSecrets object with all configuration
            
        Raises:
            ValueError: If required secrets are missing
        """
        # Required secrets
        required = {
            'DATABASE_URL': 'Database connection string',
            'JWT_SECRET': 'JWT secret key',
            'TRADINGVIEW_WEBHOOK_SECRET': 'TradingView webhook secret',
            'MT5_LOGIN': 'MT5 account login',
            'MT5_PASSWORD': 'MT5 account password',
            'MT5_SERVER': 'MT5 broker server',
        }
        
        # Check required secrets
        missing = []
        for key, description in required.items():
            if not os.getenv(key):
                missing.append(f"{key} ({description})")
        
        if missing:
            raise ValueError(
                f"Missing required secrets:\n" + "\n".join(f"  - {m}" for m in missing)
            )
        
        # Build secrets object
        secrets = TradingSecrets(
            # Database
            database_url=os.getenv('DATABASE_URL'),
            
            # JWT
            jwt_secret=os.getenv('JWT_SECRET'),
            jwt_expiration_hours=int(os.getenv('JWT_EXPIRATION_HOURS', '24')),
            
            # TradingView
            tradingview_webhook_secret=os.getenv('TRADINGVIEW_WEBHOOK_SECRET'),
            
            # API Keys
            api_key=os.getenv('API_KEY', 'default-api-key-change-me'),
            
            # MT5
            mt5_login=os.getenv('MT5_LOGIN'),
            mt5_password=os.getenv('MT5_PASSWORD'),
            mt5_server=os.getenv('MT5_SERVER'),
            
            # Redis
            redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            
            # S3/MinIO
            s3_endpoint=os.getenv('S3_ENDPOINT'),  # e.g., s3.amazonaws.com or minio:9000
            s3_access_key=os.getenv('S3_ACCESS_KEY'),
            s3_secret_key=os.getenv('S3_SECRET_KEY'),
            s3_bucket=os.getenv('S3_BUCKET', 'trading-models'),
            
            # Monitoring
            prometheus_enabled=os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true',
            alert_webhook_url=os.getenv('ALERT_WEBHOOK_URL'),
        )
        
        return secrets
    
    def validate_secrets(self) -> Dict[str, bool]:
        """
        Validate all secrets are properly set
        
        Returns:
            Dictionary of validation results
        """
        try:
            secrets = self.get_secrets()
            
            validations = {
                'database_url': bool(secrets.database_url and secrets.database_url.startswith('postgresql://')),
                'jwt_secret': len(secrets.jwt_secret) >= 32,  # Should be at least 32 chars
                'tradingview_secret': len(secrets.tradingview_webhook_secret) >= 16,
                'mt5_credentials': all([secrets.mt5_login, secrets.mt5_password, secrets.mt5_server]),
                'redis_url': bool(secrets.redis_url),
            }
            
            return validations
            
        except Exception as e:
            return {'error': str(e)}


def create_env_template(output_file: str = '.env.template'):
    """
    Create a template .env file with all required variables
    
    Args:
        output_file: Path to output template file
    """
    template = """# AI Trading System - Environment Variables Template
# Copy this file to .env and fill in your actual values

# ============================================
# DATABASE
# ============================================
DATABASE_URL=postgresql://trading_user:trading_pass@localhost:5432/trading_db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_ECHO_SQL=false

# ============================================
# SECURITY
# ============================================
JWT_SECRET=your-super-secret-jwt-key-minimum-32-characters-long
JWT_EXPIRATION_HOURS=24
API_KEY=your-api-key-for-internal-service-communication

# TradingView Webhook Secret (set in TradingView alert)
TRADINGVIEW_WEBHOOK_SECRET=your-tradingview-webhook-secret

# ============================================
# MT5 BROKER CREDENTIALS
# ============================================
MT5_LOGIN=12345678
MT5_PASSWORD=your-mt5-password
MT5_SERVER=Exness-MT5Real  # or XMGlobal-MT5

# ============================================
# REDIS
# ============================================
REDIS_URL=redis://localhost:6379/0

# ============================================
# S3 / MinIO (Model Storage)
# ============================================
S3_ENDPOINT=s3.amazonaws.com  # or localhost:9000 for MinIO
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=trading-models

# ============================================
# MONITORING
# ============================================
PROMETHEUS_ENABLED=true
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# ============================================
# RISK MANAGEMENT
# ============================================
RISK_DAILY_LOSS_LIMIT_PCT=2.0
RISK_CONSECUTIVE_LOSS_LIMIT=3
RISK_MAX_POSITION_SIZE_PCT=5.0
RISK_MAX_TOTAL_EXPOSURE_PCT=30.0

# ============================================
# AI MODEL
# ============================================
MODEL_NAME=lstm_v1  # lstm_v1, transformer_v1, lightgbm_v1
MODEL_CONFIDENCE_THRESHOLD=0.7
MODEL_INFERENCE_TIMEOUT_MS=50

# ============================================
# LLM VALIDATION (Offline Confirmation)
# ============================================
LLM_VALIDATION_ENABLED=true
LLM_MODEL=llama3  # llama3, mistral, codellama, etc.
LLM_API_ENDPOINT=http://localhost:11434  # Ollama endpoint
"""
    
    with open(output_file, 'w') as f:
        f.write(template)
    
    print(f"✅ Created environment template: {output_file}")
    print("📝 Copy to .env and fill in your actual values")


# Global secrets manager instance
secrets_manager = SecretsManager()


if __name__ == '__main__':
    # Generate .env template
    create_env_template()
