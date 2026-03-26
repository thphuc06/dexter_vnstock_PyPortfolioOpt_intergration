# Dexter AI: Vietnam Stock Investment Agent

Dexter is a professional **Autonomous AI Agent** built specifically for the Vietnamese stock market. This system merges the advanced reasoning capabilities of Large Language Models (LLMs) with the quantitative data analysis horsepower of Python.

## 🏗 System Architecture

The core logic is powered by the **ReAct (Reasoning + Acting)** framework, divided into 3 main components:

1. **Dexter (TypeScript/Bun):** 
   - The primary Orchestrator. It comprehends user intents, devises plans (Reasoning), and autonomously invokes external tools (Acting).
2. **vnstock (Python):** 
   - Responsible for scraping real-time financial reports, historical prices, and corporate information from stock APIs (VCI/KBS).
3. **PyPortfolioOpt (Python):** 
   - Handles Portfolio Optimization. It calculates precise capital allocation weights based on mathematical models (Markowitz's Efficient Frontier).

---

## 🚀 Setup & Execution

### Prerequisites:
- [Bun](https://bun.sh/) (TypeScript runtime environment)
- [Python 3.10+](https://www.python.org/)
- API Keys: AWS Bedrock/OpenAI/Gemini (Configure inside `dexter/.env`)

### 1. Standalone CLI Mode
Use this mode to interact directly with Dexter via the terminal for debugging or personal use.

**Start the Data Backend (Python):**
```bash
# Terminal 1
cd vnstock
python -m venv venv
.\venv\Scripts\activate   # (Use 'source venv/bin/activate' on Mac/Linux)
pip install -r requirements.txt
python vnstock_service.py
```

**Run the Agent (TypeScript):**
```bash
# Terminal 2
cd dexter
bun install
bun run cli "Analyze FPT today and create an investment portfolio with FPT, VCB, HPG"
```

### 2. API Server Mode
Use this mode to expose an API Endpoint that external applications (Web/App Frontends) can connect to.

**Start the Data Backend (Python):** 
*(Identical to Step 1)*

**Start the Dexter API Server:**
```bash
# Terminal 2
cd dexter
bun install
bun run server
```

**API Testing:**
The server will run at `http://localhost:3000`. You can send a POST request to the `/ask` endpoint with the following JSON Body structure:

```typescript
{
  "question": string,         // Required: The analytical query
  "model"?: string,           // Optional: LLM model ID
  "modelProvider"?: string,   // Optional: Provider name (e.g., bedrock)
  "maxIterations"?: number    // Optional: Max tool calls allowed (e.g., 2 for faster response)
}
```

```powershell
# PowerShell Invocation Example
$uri = "http://localhost:3000/ask"
$body = @{
    question      = "Give me a quick update on the stock market today"
    model         = "bedrock:us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    maxIterations = 2
} | ConvertTo-Json -Compress
$headers = @{ "Content-Type" = "application/json; charset=utf-8" }

Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body
```

---
