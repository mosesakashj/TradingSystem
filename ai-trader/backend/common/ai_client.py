from typing import Dict
import random
import sys
import os

# Add backend to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.model.llm_validator import llm_validator

class AIClient:
    def __init__(self):
        self.validator = llm_validator

    async def get_prediction(self, signal_data: Dict) -> Dict:
        """
        Get prediction from AI Inference Service.
        For now, we mock this as the ML service might not be running.
        """
        # Mock logic based on signal direction and random factors
        direction = signal_data.get('direction', 'buy')
        is_buy = direction.lower() == 'buy'
        
        # Simulate model confidence
        # If it's a "good" signal (mocked), give high score
        base_score = 0.65 + (random.random() * 0.3) # 0.65 - 0.95
        
        return {
            'model_name': 'lstm_ensemble_v2',
            'prediction': base_score if is_buy else (1 - base_score), # >0.5 for buy
            'confidence': 0.75 + (random.random() * 0.20), # 0.75 - 0.95
            'expected_return': 0.8 + (random.random() * 2.2), # 0.8% - 3.0%
            'features': {
                'rsi': 30 + (random.random() * 40),
                'macd': 0.001 * (random.random() - 0.5),
                'volatility': 0.01 + (random.random() * 0.02),
                'volume_trend': 'increasing' if random.random() > 0.4 else 'stable'
            }
        }

    async def validate_signal(self, signal_data: Dict, prediction: Dict, risk_assessment: Dict) -> Dict:
        """
        Validate using LLM
        """
        # Run in thread pool to avoid blocking
        import asyncio
        
        approved, reasoning, confidence = await asyncio.to_thread(
            self.validator.validate_signal,
            signal_data, prediction, risk_assessment
        )
        
        return {
            'approved': approved,
            'reasoning': reasoning,
            'confidence': confidence
        }

ai_client = AIClient()
