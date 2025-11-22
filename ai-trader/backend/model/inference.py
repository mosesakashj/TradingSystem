# AI Inference Service - Model Serving
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import torch
import numpy as np
import pandas as pd
from datetime import datetime
import os
import pickle

# Model imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.features.engineer import FeatureEngineer
from ml.models.lstm import LSTMTradingModel


class PredictionRequest(BaseModel):
    """Prediction request schema"""
    signal_id: int
    symbol: str
    direction: str
    historical_data: List[Dict]  # OHLCV data


class PredictionResponse(BaseModel):
    """Prediction response schema"""
    signal_id: int
    model_name: str
    model_version: str
    prediction: float  # 0-1 probability
    confidence: float  # 0-1
    expected_return: Optional[float]
    inference_time_ms: float
    features: Dict


class ModelRegistry:
    """Registry for managing multiple models"""
    
    def __init__(self):
        self.models = {}
        self.feature_engineer = FeatureEngineer()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    def load_model(
        self,
        model_name: str,
        model_path: str,
        model_type: str = 'lstm'
    ):
        """
        Load model from path
        
        Args:
            model_name: Model identifier
            model_path: Path to model file
            model_type: Type of model (lstm, transformer, lightgbm)
        """
        print(f"Loading {model_type} model: {model_name} from {model_path}")
        
        if model_type == 'lstm':
            # Load LSTM model
            model = LSTMTradingModel(
                input_size=50,  # Will be determined by features
                hidden_size=128,
                num_layers=2,
                dropout=0.2,
                bidirectional=True,
                use_attention=True
            )
            
            if os.path.exists(model_path):
                model.load_state_dict(torch.load(model_path, map_location=self.device))
                model.to(self.device)
                model.eval()
                print(f"✅ Loaded LSTM model from {model_path}")
            else:
                print(f"⚠️  Model file not found: {model_path}, using untrained model")
        
        elif model_type == 'lightgbm':
            # Load LightGBM model
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                print(f"✅ Loaded LightGBM model from {model_path}")
            else:
                print(f"⚠️  Model file not found: {model_path}")
                model = None
        
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        self.models[model_name] = {
            'model': model,
            'type': model_type,
            'loaded_at': datetime.utcnow()
        }
    
    def get_model(self, model_name: str):
        """Get loaded model"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded")
        return self.models[model_name]
    
    def predict(
        self,
        model_name: str,
        features: np.ndarray
    ) -> Tuple[float, float]:
        """
        Make prediction using specified model
        
        Args:
            model_name: Model to use
            features: Feature array
            
        Returns:
            (prediction, confidence) tuple
        """
        model_info = self.get_model(model_name)
        model = model_info['model']
        model_type = model_info['type']
        
        if model_type == 'lstm':
            # LSTM prediction
            with torch.no_grad():
                x = torch.FloatTensor(features).unsqueeze(0).to(self.device)
                pred = model(x).cpu().numpy()[0][0]
                confidence = abs(pred - 0.5) * 2  # Distance from 0.5, scaled to [0,1]
                return float(pred), float(confidence)
        
        elif model_type == 'lightgbm':
            # LightGBM prediction
            pred = model.predict_proba(features.reshape(1, -1))[0][1]
            confidence = abs(pred - 0.5) * 2
            return float(pred), float(confidence)
        
        else:
            raise ValueError(f"Unknown model type: {model_type}")


# FastAPI app
app = FastAPI(
    title="AI Inference Service",
    description="ML model serving for trading signal validation",
    version="1.0.0"
)

# Global model registry
registry = ModelRegistry()


@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    print("🚀 Starting AI Inference Service...")
    
    # Load default LSTM model
    model_path = os.getenv('LSTM_MODEL_PATH', 'models/lstm_v1.pth')
    try:
        registry.load_model('lstm_v1', model_path, 'lstm')
    except Exception as e:
        print(f"⚠️  Failed to load LSTM model: {e}")
    
    # Load LightGBM model (if available)
    lgbm_path = os.getenv('LIGHTGBM_MODEL_PATH', 'models/lightgbm_v1.pkl')
    if os.path.exists(lgbm_path):
        try:
            registry.load_model('lightgbm_v1', lgbm_path, 'lightgbm')
        except Exception as e:
            print(f"⚠️  Failed to load LightGBM model: {e}")
    
    print("✅ AI Inference Service started")


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "ai_inference",
        "models_loaded": list(registry.models.keys()),
        "device": str(registry.device)
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Make prediction for a trading signal
    
    Args:
        request: Prediction request with historical data
        
    Returns:
        Prediction with confidence score
    """
    import time
    start_time = time.time()
    
    # Get model name from environment (allow A/B testing)
    model_name = os.getenv('ACTIVE_MODEL', 'lstm_v1')
    
    try:
        # Convert historical data to DataFrame
        df = pd.DataFrame(request.historical_data)
        
        # Ensure required columns
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            raise HTTPException(status_code=400, detail="Missing OHLCV columns in historical_data")
        
        # Engineer features
        df_features = registry.feature_engineer.engineer_features(
            df,
            symbol=request.symbol,
            timeframe='1h'  # Can be passed in request
        )
        
        # Get latest features (last row)
        if len(df_features) == 0:
            raise HTTPException(status_code=400, detail="Not enough data to engineer features")
        
        feature_values = df_features[registry.feature_engineer.feature_names].iloc[-1].values
        
        # Make prediction
        prediction, confidence = registry.predict(model_name, feature_values)
        
        # Calculate expected return (placeholder - can be enhanced)
        expected_return = (prediction - 0.5) * 2.0 * 100  # Convert to % estimate
        
        inference_time_ms = (time.time() - start_time) * 1000
        
        return PredictionResponse(
            signal_id=request.signal_id,
            model_name=model_name,
            model_version='1.0',
            prediction=prediction,
            confidence=confidence,
            expected_return=expected_return,
            inference_time_ms=inference_time_ms,
            features={
                name: float(value)
                for name, value in zip(registry.feature_engineer.feature_names[:10], feature_values[:10])
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/models")
async def list_models():
    """List all loaded models"""
    return {
        "models": [
            {
                "name": name,
                "type": info['type'],
                "loaded_at": info['loaded_at'].isoformat()
            }
            for name, info in registry.models.items()
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "inference:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
