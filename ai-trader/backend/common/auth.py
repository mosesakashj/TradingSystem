# Common utilities - Authentication and Security
import hashlib
import hmac
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class AuthConfig:
    """Authentication configuration"""
    JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    
    TRADINGVIEW_SECRET = os.getenv('TRADINGVIEW_WEBHOOK_SECRET', 'your-tradingview-webhook-secret')
    API_KEY = os.getenv('API_KEY', 'your-api-key-for-internal-services')


auth_config = AuthConfig()
security = HTTPBearer()


class PasswordManager:
    """Password hashing and verification using bcrypt"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storing"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a stored password against one provided by user"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


class JWTManager:
    """JWT token generation and validation"""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        
        Args:
            data: Dictionary with user data (e.g., {"sub": "username"})
            expires_delta: Custom expiration time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=auth_config.JWT_EXPIRATION_HOURS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow()
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            auth_config.JWT_SECRET,
            algorithm=auth_config.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict:
        """
        Decode and validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                auth_config.JWT_SECRET,
                algorithms=[auth_config.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )


class WebhookSignatureValidator:
    """HMAC signature validation for TradingView webhooks"""
    
    @staticmethod
    def generate_signature(payload: str, secret: str = None) -> str:
        """
        Generate HMAC SHA256 signature for payload
        
        Args:
            payload: Raw payload string
            secret: Secret key (defaults to TradingView secret)
            
        Returns:
            Hex digest of signature
        """
        if secret is None:
            secret = auth_config.TRADINGVIEW_SECRET
        
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def validate_signature(payload: str, received_signature: str, secret: str = None) -> bool:
        """
        Validate HMAC signature
        
        Args:
            payload: Raw payload string
            received_signature: Signature from webhook header
            secret: Secret key (defaults to TradingView secret)
            
        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = WebhookSignatureValidator.generate_signature(payload, secret)
        return hmac.compare_digest(expected_signature, received_signature)


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict:
    """
    FastAPI dependency for JWT authentication
    
    Usage:
        @app.get("/protected")
        def protected_route(token_data: dict = Depends(verify_jwt_token)):
            return {"user": token_data["sub"]}
    """
    token = credentials.credentials
    return JWTManager.decode_token(token)


def verify_api_key(api_key: str) -> bool:
    """
    Verify API key for internal service-to-service communication
    
    Args:
        api_key: API key to verify
        
    Returns:
        True if valid, False otherwise
    """
    return hmac.compare_digest(api_key, auth_config.API_KEY)


# Rate limiting (simple in-memory implementation)
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}  # {key: [timestamp1, timestamp2, ...]}
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Unique identifier (IP, user ID, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Initialize or clean old requests
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old timestamps
        self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]
        
        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()
