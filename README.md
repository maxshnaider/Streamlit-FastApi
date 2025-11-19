# Streamlit + FastAPI Crypto Advisor

Simple project for generating crypto trading tips using Gemini or OpenAI models,  
with token-based cost estimation and an internal SQLite wallet.

---

##  Features

- Request trading advice for **BTC / ETH / SOL**
- Choose LLM model: **Gemini 2.5 Flash** or **OpenAI gpt-4o-mini**
- Automatic token usage & cost calculation

---

##  Installation

### 1. Create & activate virtual environment

**Windows**
python -m venv .venv
.venv\Scripts\activate

**macOS / Linux**
python3 -m venv .venv
source .venv/bin/activate

### 2. Install dependencies
pip install -r requirements.txt

(Optional) Install developer tools

pip install -r requirements-dev.txt


### 3. Create .env file

GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key
ADVISOR_API_URL=http://127.0.0.1:8000

### 4. Run the project

Start FastAPI backend:

uvicorn app.main:app --reload

Docs: http://127.0.0.1:8000/docs

Start Streamlit UI:

streamlit run front/main.py
