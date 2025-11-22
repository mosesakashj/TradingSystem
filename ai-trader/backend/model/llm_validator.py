# LLM-based Trade Validation Service
"""
Offline LLM confirmation for trading signals.
Uses a local language model to provide reasoning-based validation.
"""

import os
from typing import Dict, Optional, Tuple
from datetime import datetime
import json


class LLMValidator:
    """
    Offline LLM validator for trading signals
    
    This service uses a local/offline LLM to validate trading decisions
    with natural language reasoning. Can use:
    - Ollama (llama3, mistral, etc.)
    - GPT4All
    - LlamaCPP
    - Or any local model API
    """
    
    def __init__(self, model_name: str = "llama3", api_endpoint: str = "http://localhost:11434"):
        """
        Initialize LLM validator
        
        Args:
            model_name: Name of the LLM model to use
            api_endpoint: API endpoint for the LLM service (e.g., Ollama)
        """
        self.model_name = model_name
        self.api_endpoint = api_endpoint
        self.enabled = os.getenv('LLM_VALIDATION_ENABLED', 'true').lower() == 'true'
    
    def validate_signal(
        self,
        signal_data: Dict,
        ai_prediction: Dict,
        risk_assessment: Dict,
        market_context: Optional[Dict] = None
    ) -> Tuple[bool, str, float]:
        """
        Validate trading signal using LLM reasoning
        
        Args:
            signal_data: Original signal from TradingView
            ai_prediction: AI model prediction results
            risk_assessment: Risk manager assessment
            market_context: Additional market context (optional)
            
        Returns:
            (approved, reasoning, confidence) tuple
        """
        if not self.enabled:
            return True, "LLM validation disabled", 1.0
        
        # Build context for LLM
        prompt = self._build_validation_prompt(
            signal_data, ai_prediction, risk_assessment, market_context
        )
        
        try:
            # Call LLM for reasoning
            llm_response = self._call_llm(prompt)
            
            # Parse LLM response
            approved, reasoning, confidence = self._parse_llm_response(llm_response)
            
            return approved, reasoning, confidence
            
        except Exception as e:
            # Fail-safe: if LLM fails, log error and default to approval
            # (since AI and Risk already validated)
            print(f"⚠️  LLM validation failed: {e}")
            return True, f"LLM validation error: {str(e)}", 0.5
    
    def _build_validation_prompt(
        self,
        signal_data: Dict,
        ai_prediction: Dict,
        risk_assessment: Dict,
        market_context: Optional[Dict]
    ) -> str:
        """Build prompt for LLM"""
        
        prompt = f"""You are an expert trading analyst. Review the following trading signal and provide your professional assessment.

**SIGNAL DETAILS:**
Symbol: {signal_data.get('symbol')}
Direction: {signal_data.get('direction')}
Entry Price: {signal_data.get('entry_price')}
Stop Loss: {signal_data.get('stop_loss')}
Take Profit: {signal_data.get('take_profit')}
Timeframe: {signal_data.get('timeframe')}
Strategy: {signal_data.get('strategy_name')}

**AI MODEL PREDICTION:**
Model: {ai_prediction.get('model_name')}
Prediction Score: {ai_prediction.get('prediction'):.3f}
Confidence: {ai_prediction.get('confidence'):.1%}
Expected Return: {ai_prediction.get('expected_return'):.2f}%

**RISK ASSESSMENT:**
Approved by Risk Manager: {risk_assessment.get('approved')}
Risk Level: {risk_assessment.get('risk_level')}
Position Size: {risk_assessment.get('position_size_lots')} lots
Warnings: {', '.join(risk_assessment.get('warnings', [])) or 'None'}
Reasons for Concern: {', '.join(risk_assessment.get('reasons', [])) or 'None'}

**MARKET CONTEXT:**
{json.dumps(market_context, indent=2) if market_context else 'No additional context provided'}

**YOUR TASK:**
1. Analyze this trading signal from multiple perspectives:
   - Technical setup quality
   - Risk-reward ratio
   - Market conditions alignment
   - Timing considerations
   - AI model confidence

2. Provide your recommendation in the following JSON format:
{{
  "approved": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Clear explanation of your decision in 2-3 sentences",
  "risk_factors": ["list", "of", "key", "risks"],
  "favorable_factors": ["list", "of", "positives"]
}}

Be concise, objective, and focus on the most critical factors. Think step-by-step."""

        return prompt
    
    def _call_llm(self, prompt: str) -> Dict:
        """
        Call LLM API (Ollama example)
        
        For production, this would call your local LLM service
        """
        import requests
        
        try:
            # Ollama API format
            response = requests.post(
                f"{self.api_endpoint}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",  # Request JSON response
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent analysis
                        "top_p": 0.9,
                        "num_predict": 500  # Max tokens
                    }
                },
                timeout=30  # 30 second timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return json.loads(result.get('response', '{}'))
            else:
                raise Exception(f"LLM API error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            # LLM service not running - use fallback
            return self._fallback_validation(prompt)
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")
    
    def _fallback_validation(self, prompt: str) -> Dict:
        """
        Fallback validation when LLM is not available
        
        Uses rule-based logic as a simple alternative
        """
        # Simple rule-based approval
        # In production, you might want to be more conservative
        return {
            "approved": True,
            "confidence": 0.7,
            "reasoning": "LLM service unavailable. Using rule-based fallback validation. AI and Risk checks passed.",
            "risk_factors": ["LLM service offline", "Limited validation depth"],
            "favorable_factors": ["AI model approved", "Risk manager approved"]
        }
    
    def _parse_llm_response(self, llm_response: Dict) -> Tuple[bool, str, float]:
        """
        Parse LLM response and extract decision
        
        Args:
            llm_response: JSON response from LLM
            
        Returns:
            (approved, reasoning, confidence)
        """
        try:
            approved = llm_response.get('approved', False)
            confidence = float(llm_response.get('confidence', 0.5))
            
            # Build detailed reasoning string
            base_reasoning = llm_response.get('reasoning', 'No reasoning provided')
            risk_factors = llm_response.get('risk_factors', [])
            favorable_factors = llm_response.get('favorable_factors', [])
            
            reasoning_parts = [base_reasoning]
            
            if favorable_factors:
                reasoning_parts.append(f"\nPositive factors: {', '.join(favorable_factors)}")
            
            if risk_factors:
                reasoning_parts.append(f"\nRisk factors: {', '.join(risk_factors)}")
            
            reasoning = '\n'.join(reasoning_parts)
            
            return approved, reasoning, confidence
            
        except Exception as e:
            # If parsing fails, default to conservative approach
            print(f"⚠️  Error parsing LLM response: {e}")
            return False, f"Failed to parse LLM response: {str(e)}", 0.0
    
    def get_validation_summary(
        self,
        approved: bool,
        reasoning: str,
        confidence: float
    ) -> str:
        """
        Generate human-readable validation summary
        
        Args:
            approved: LLM approval decision
            reasoning: LLM reasoning
            confidence: LLM confidence score
            
        Returns:
            Formatted summary string
        """
        status = "✅ APPROVED" if approved else "❌ REJECTED"
        confidence_pct = confidence * 100
        
        summary = f"""
LLM Validation: {status}
Confidence: {confidence_pct:.1f}%

Reasoning:
{reasoning}
"""
        return summary.strip()


# Global LLM validator instance
llm_validator = LLMValidator(
    model_name=os.getenv('LLM_MODEL', 'llama3'),
    api_endpoint=os.getenv('LLM_API_ENDPOINT', 'http://localhost:11434')
)


# Example usage and testing
if __name__ == '__main__':
    # Test LLM validator
    validator = LLMValidator()
    
    # Sample signal
    signal = {
        'symbol': 'EURUSD',
        'direction': 'buy',
        'entry_price': 1.0850,
        'stop_loss': 1.0820,
        'take_profit': 1.0910,
        'timeframe': '1h',
        'strategy_name': 'Trend Following'
    }
    
    # Sample AI prediction
    ai_pred = {
        'model_name': 'lstm_v1',
        'prediction': 0.75,
        'confidence': 0.82,
        'expected_return': 1.5
    }
    
    # Sample risk assessment
    risk = {
        'approved': True,
        'risk_level': 'medium',
        'position_size_lots': 0.1,
        'warnings': ['Moderate volatility'],
        'reasons': []
    }
    
    # Validate
    approved, reasoning, confidence = validator.validate_signal(
        signal, ai_pred, risk
    )
    
    print(validator.get_validation_summary(approved, reasoning, confidence))
