# LLM Validation Setup Guide

## Overview

The trading system now includes an **offline LLM validation layer** that provides natural language reasoning for trade approval. This adds an extra layer of confidence before executing trades.

## Pipeline Flow

```
TradingView Signal
    ↓
Webhook Service (Signature Validation)
    ↓
Store Raw Signal in Database
    ↓
AI Inference Service (LSTM/ML Prediction)
    ↓
🆕 LLM Validator (Reasoning-based Confirmation)
    ↓
Risk Manager (Position Sizing, Circuit Breakers)
    ↓
MT5 Execution (If All Approved)
    ↓
Log Trade + AI Reasoning
    ↓
Show in UI with LLM Reasoning
```

---

## LLM Options

### Option 1: Ollama (Recommended)

**Pros**: Free, fast, runs locally, easy setup  
**Models**: llama3, mistral, codellama, phi3

#### Installation

```bash
# Install Ollama
# Windows
winget install Ollama.Ollama

# Or download from https://ollama.ai

# Pull a model
ollama pull llama3

# Start Ollama (runs on http://localhost:11434)
ollama serve
```

#### Configuration

```env
# .env file
LLM_VALIDATION_ENABLED=true
LLM_MODEL=llama3
LLM_API_ENDPOINT=http://localhost:11434
```

---

### Option 2: GPT4All

**Pros**: GUI application, easy for non-technical users  
**Cons**: Slower than Ollama

#### Installation

1. Download GPT4All from https://gpt4all.io
2. Install and select a model (e.g., Mistral)
3. Enable API server in settings

#### Configuration

```env
LLM_VALIDATION_ENABLED=true
LLM_MODEL=mistral
LLM_API_ENDPOINT=http://localhost:4891
```

---

### Option 3: LlamaCPP Server

**Pros**: Very fast, customizable  
**Cons**: Requires manual model download

#### Installation

```bash
# Install llama-cpp-python with server
pip install 'llama-cpp-python[server]'

# Download a model (e.g., from HuggingFace)
# Run server
python -m llama_cpp.server --model /path/to/model.gguf
```

---

### Option 4: Disable LLM Validation

If you don't want to use LLM validation:

```env
LLM_VALIDATION_ENABLED=false
```

The system will skip LLM validation and proceed directly from AI inference to risk management.

---

## How It Works

### 1. Signal Analysis

When a signal arrives, the LLM receives:
- **Signal details**: Symbol, direction, entry/SL/TP levels
- **AI prediction**: Model score, confidence, expected return
- **Risk assessment**: Preliminary risk level, warnings
- **Market context**: Optional additional data

### 2. LLM Reasoning

The LLM analyzes the signal and provides:

```json
{
  "approved": true,
  "confidence": 0.85,
  "reasoning": "Strong bullish setup with good risk-reward ratio. MACD showing momentum...",
  "risk_factors": ["High volatility", "Near resistance"],
  "favorable_factors": ["Trend alignment", "Strong AI confidence", "Good RR ratio"]
}
```

### 3. Decision Making

- If **LLM approves** → Continue to Risk Manager
- If **LLM rejects** → Stop and log rejection reason
- If **LLM fails** → Fallback to rule-based validation (fail-safe)

### 4. Database Storage

All LLM reasoning is stored in the database:

```python
prediction.llm_approved = True
prediction.llm_reasoning = "Strong bullish setup with..."
prediction.llm_confidence = 0.85
```

### 5. UI Display

The dashboard shows LLM reasoning for each trade, helping you understand why trades were approved or rejected.

---

## Example LLM Response

```
LLM Validation: ✅ APPROVED
Confidence: 85.0%

Reasoning:
Strong bullish setup with favorable risk-reward ratio of 2:1. The AI model shows
high confidence (82%) and expected return is positive. MACD crossover confirms
momentum in the buy direction.

Positive factors: Trend alignment, Strong AI confidence, Good RR ratio
Risk factors: High volatility, Near resistance level
```

---

## Performance Considerations

### Latency Impact

- **Ollama (llama3)**: ~500ms - 2s per validation
- **GPT4All**: ~1s - 3s per validation
- **Disabled**: 0ms (skipped)

### Recommended Settings

For **fast execution** (<500ms total):
- Use smaller models (phi3, tinyllama)
- Or disable LLM validation for high-frequency trading

For **better reasoning** (quality over speed):
- Use llama3 or mistral
- Acceptable for swing trading or position trading

---

## Testing LLM Validation

### 1. Test LLM Service

```bash
# Test Ollama is running
curl http://localhost:11434/api/generate -d '{
  "model": "llama3",
  "prompt": "Analyze this trade: Buy EURUSD at 1.0850",
  "stream": false
}'
```

### 2. Test in Python

```bash
cd backend/model
python llm_validator.py
```

### 3. Send Test Signal

```bash
curl -X POST http://localhost:8000/webhook/signal \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "direction": "buy",
    "entry_price": 1.0850,
    "stop_loss": 1.0820,
    "take_profit": 1.0910
  }'
```

Check logs for LLM reasoning:
```bash
docker-compose logs -f webhook_service | grep "LLM"
```

---

## Customization

### Customize LLM Prompt

Edit `backend/model/llm_validator.py`:

```python
def _build_validation_prompt(self, ...):
    prompt = f"""You are a professional trader with 10 years experience.
    
    Analyze this trade opportunity:
    {signal_data}
    
    Focus on:
    1. Risk-reward ratio
    2. Market trend alignment
    3. Entry timing
    
    Provide your recommendation...
    """
    return prompt
```

### Adjust Temperature

Lower temperature = more consistent  
Higher temperature = more creative

```python
"options": {
    "temperature": 0.3,  # 0.0 - 1.0
    "top_p": 0.9
}
```

---

## Troubleshooting

### LLM Service Not Running

**Error**: `Connection refused to localhost:11434`

**Solution**:
```bash
# Start Ollama
ollama serve

# Or check if running
curl http://localhost:11434
```

### LLM Too Slow

**Solution 1**: Use smaller model
```env
LLM_MODEL=phi3  # Faster than llama3
```

**Solution 2**: Reduce max tokens
```python
"num_predict": 300  # Reduce from 500
```

**Solution 3**: Disable for high-frequency
```env
LLM_VALIDATION_ENABLED=false
```

### LLM Returns Invalid JSON

The system has fallback logic:
- If JSON parsing fails, defaults to rejection
- Logs error for debugging
- Never crashes the pipeline

---

## Security Notes

✅ **Fully Offline**: No data sent to external APIs  
✅ **Privacy**: All signal data stays on your server  
✅ **Control**: You own the model and infrastructure  

---

## Recommended Models

| Model | Speed | Quality | RAM | Best For |
|-------|-------|---------|-----|----------|
| **llama3:8b** | Medium | High | 8GB | General trading |
| **mistral:7b** | Medium | High | 8GB | Complex analysis |
| **phi3:mini** | Fast | Good | 4GB | High-frequency |
| **codellama:7b** | Medium | Medium | 8GB | Technical patterns |

---

## Next Steps

1. Install Ollama and pull llama3
2. Enable LLM validation in .env
3. Restart services: `docker-compose restart`
4. Send test signal and check LLM reasoning
5. Review LLM decisions in dashboard
6. Adjust prompts for your trading style

**Happy Trading! 🚀**
