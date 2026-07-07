# Model and Temperature Configuration

The contract review system allows configuring the Claude model and temperature settings via environment variables for both the router (classification) and analysis stages.

## Environment Variables

### Model Selection

| Variable | Default | Description |
|----------|---------|-------------|
| `ROUTER_MODEL` | `claude-sonnet-4-5-20250929` | Model used for contract classification |
| `ANALYSIS_MODEL` | `claude-sonnet-4-5-20250929` | Model used for detailed contract analysis |

### Temperature Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ROUTER_TEMPERATURE` | `0.1` | Temperature for classification (0.0-1.0) |
| `ANALYSIS_TEMPERATURE` | `0.3` | Temperature for analysis (0.0-1.0) |

## Temperature Guidelines

**Lower values (0.0-0.3):**
- More deterministic and consistent
- Better for classification and structured analysis
- Recommended for production use

**Medium values (0.4-0.7):**
- Balanced creativity and consistency
- Good for exploratory analysis

**Higher values (0.7-1.0):**
- More creative and varied responses
- May produce less consistent results
- Generally not recommended for legal analysis

## Available Models

### Production Models (Recommended)

- **`claude-sonnet-4-5-20250929`** (Default)
  - Best balance of speed, cost, and quality
  - Recommended for most use cases
  - ~$3 per million input tokens, ~$15 per million output tokens

- **`claude-opus-4-5-20251101`**
  - Highest quality and reasoning capability
  - Best for complex legal analysis
  - ~$15 per million input tokens, ~$75 per million output tokens
  - Use when: Maximum accuracy is required, complex contracts

### Fast Models (Cost-Optimized)

- **`claude-haiku-3-5-20241022`**
  - Fastest and most cost-effective
  - ~$1 per million input tokens, ~$5 per million output tokens
  - Use when: High volume processing, simple contracts

## Configuration Examples

### Production (Balanced - Default)
```bash
ROUTER_MODEL=claude-sonnet-4-5-20250929
ROUTER_TEMPERATURE=0.1
ANALYSIS_MODEL=claude-sonnet-4-5-20250929
ANALYSIS_TEMPERATURE=0.3
```

### High Quality (Maximum Accuracy)
```bash
ROUTER_MODEL=claude-sonnet-4-5-20250929
ROUTER_TEMPERATURE=0.05
ANALYSIS_MODEL=claude-opus-4-5-20251101
ANALYSIS_TEMPERATURE=0.2
```

### Cost-Optimized (High Volume)
```bash
ROUTER_MODEL=claude-haiku-3-5-20241022
ROUTER_TEMPERATURE=0.1
ANALYSIS_MODEL=claude-haiku-3-5-20241022
ANALYSIS_TEMPERATURE=0.3
```

### Testing/Development
```bash
ROUTER_MODEL=claude-sonnet-4-5-20250929
ROUTER_TEMPERATURE=0.2
ANALYSIS_MODEL=claude-sonnet-4-5-20250929
ANALYSIS_TEMPERATURE=0.5
```

## How to Configure

### Railway (Production)

1. Go to your Railway project
2. Navigate to Variables tab
3. Add environment variables:
   ```
   ROUTER_MODEL=claude-sonnet-4-5-20250929
   ROUTER_TEMPERATURE=0.1
   ANALYSIS_MODEL=claude-sonnet-4-5-20250929
   ANALYSIS_TEMPERATURE=0.3
   ```
4. Deploy changes

### Local Development

1. Create/edit `.env` file in `backend/` directory:
   ```bash
   ROUTER_MODEL=claude-sonnet-4-5-20250929
   ROUTER_TEMPERATURE=0.1
   ANALYSIS_MODEL=claude-sonnet-4-5-20250929
   ANALYSIS_TEMPERATURE=0.3
   ```
2. Restart the backend server

## Metadata Tracking

Model and temperature settings are automatically tracked in the contract analysis results:

### Router Classification Metadata
```json
{
  "router_classification": {
    "classification": "vendor",
    "confidence_score": 95,
    "reasoning": "...",
    "key_signals": [...],
    "model_metadata": {
      "model": "claude-sonnet-4-5-20250929",
      "temperature": 0.1,
      "stage": "classification"
    }
  }
}
```

### Analysis Metadata
```json
{
  "model_metadata": {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.3,
    "stage": "analysis",
    "contract_type": "vendor"
  }
}
```

This metadata is stored in the `full_analysis` JSONB field in the database and can be used for:
- Auditing which model version was used
- A/B testing different models or temperatures
- Reproducing analyses with exact settings
- Cost tracking and optimization

## Recommendations

### For Demos and Testing
- Use default Sonnet 4.5 configuration
- Keep temperatures low (0.1 for router, 0.3 for analysis)

### For Production
- Start with Sonnet 4.5 defaults
- Monitor accuracy and adjust if needed
- Consider Opus for high-stakes contracts only

### For Cost Optimization
- Use Haiku for simple contracts
- Use Sonnet for standard contracts
- Reserve Opus for complex/high-value contracts

## Monitoring

Check logs for model metadata on each analysis:
```
🤖 Model: claude-sonnet-4-5-20250929, Temperature: 0.1
```

Query database for model usage:
```sql
SELECT
  full_analysis->'model_metadata'->>'model' as model,
  full_analysis->'model_metadata'->>'temperature' as temperature,
  COUNT(*) as count
FROM contract_analyses
GROUP BY 1, 2;
```
