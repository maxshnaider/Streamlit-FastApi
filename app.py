from enum import StrEnum
from typing import Tuple
from fastapi import FastAPI, Query, HTTPException, Form, Depends
from pydantic import BaseModel
import google.generativeai as genai
from openai import OpenAI
import tiktoken
import os
from dotenv import load_dotenv
from wallet import (
    init_db,
    create_user,
    get_balance,
    deduct_balance,
    get_user_info,
)  # + get_user_info

load_dotenv()

init_db()
create_user("admin", start_balance=0.05)
create_user("user", start_balance=0.05)

AUTH = {"admin": "admin", "user": "user"}

app = FastAPI(title="Gemini/OpenAI Bitcoin Advisor")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class Coin(StrEnum):
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"


class LLModel(StrEnum):
    GEMINI_FLASH = "models/gemini-2.5-flash"
    OPENAI_MINI = "gpt-4o-mini"


class PricePer1K(BaseModel):
    in_price: float
    out_price: float


class UsageTokens(BaseModel):
    in_tokens: int
    out_tokens: int
    total: int


class AdviceResponse(BaseModel):
    reply: str
    coin: Coin
    model: LLModel
    price_per_1k: PricePer1K
    usage_tokens: UsageTokens
    estimated_cost_usd: float
    user_balance_usd: float
    deducted_usd: float


PRICES = {
    LLModel.GEMINI_FLASH: {"in": 0.00010, "out": 0.00040},
    LLModel.OPENAI_MINI: {"in": 0.00015, "out": 0.00060},
}
EXPECTED_OUT_TOKENS = 90


def build_prompt(coin: Coin) -> str:
    return (
        f"Give a short, practical trading tip for {coin} for today. "
        f"Max 3 sentences. No price guarantees; focus on risk management."
    )


def quote(model: LLModel) -> PricePer1K:
    p = PRICES[model]
    return PricePer1K(in_price=p["in"], out_price=p["out"])


def estimate_tokens_for_model(model: LLModel, prompt: str) -> int:
    try:
        if model == LLModel.OPENAI_MINI:
            enc = tiktoken.encoding_for_model("gpt-4o-mini")
        else:
            enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(prompt))


def estimate_cost(in_tokens: int, out_tokens: int, price: PricePer1K) -> float:
    return (in_tokens / 1000.0) * price.in_price + (
        out_tokens / 1000.0
    ) * price.out_price


def call_llm(model: LLModel, prompt: str) -> Tuple[str, int, int, int]:
    try:
        if model == LLModel.GEMINI_FLASH:
            g = genai.GenerativeModel(model.value)
            res = g.generate_content(prompt)
            text = (getattr(res, "text", None) or "").strip()
            if not text:
                raise ValueError("Empty response from Gemini")

            usage = getattr(res, "usage_metadata", None)
            if usage:
                in_t = int(getattr(usage, "prompt_token_count", 0) or 0)
                out_t = int(getattr(usage, "candidates_token_count", 0) or 0)
                total = int(
                    getattr(usage, "total_token_count", in_t + out_t) or (in_t + out_t)
                )
            else:
                in_t = out_t = total = 0
            return text, in_t, out_t, total

        elif model == LLModel.OPENAI_MINI:
            res = openai_client.responses.create(model=model.value, input=prompt)
            text = (getattr(res, "output_text", "") or "").strip()
            if not text:
                raise ValueError("Empty response from OpenAI")

            u = getattr(res, "usage", None)
            in_t = int(getattr(u, "input_tokens", 0) or 0)
            out_t = int(getattr(u, "output_tokens", 0) or 0)
            total = int(getattr(u, "total_tokens", in_t + out_t) or (in_t + out_t))
            return text, in_t, out_t, total

        else:
            raise HTTPException(status_code=400, detail="Unknown model")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


def auth_dep(
    username: str = Query(..., description="account username (admin/user)"),
    password: str = Query(..., description="password (admin/user)"),
) -> str:
    if username not in AUTH or AUTH[username] != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return username


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username not in AUTH or AUTH[username] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "balance": round(get_balance(username), 6)}


@app.get("/user")
def get_user(username: str = Depends(auth_dep)):
    info = get_user_info(username)
    if not info:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": username, **info}


@app.get("/estimate")
def estimate_cost_ep(
    coin: Coin = Query(..., description="BTC / ETH / SOL"),
    model: LLModel = Query(..., description="GEMINI_FLASH / OPENAI_MINI"),
    username: str = Depends(auth_dep),
):
    prompt = build_prompt(coin)
    in_tokens = estimate_tokens_for_model(model, prompt)
    out_tokens = EXPECTED_OUT_TOKENS
    price = quote(model)
    cost = estimate_cost(in_tokens, out_tokens, price)

    balance = get_balance(username)
    return {
        "coin": coin,
        "model": model,
        "estimated_tokens": {
            "in": in_tokens,
            "out": out_tokens,
            "total": in_tokens + out_tokens,
        },
        "estimated_cost_usd": round(cost, 6),
        "user_balance_usd": round(balance, 6),
        "predicted_balance_usd": round(max(balance - cost, 0.0), 6),
    }


@app.get("/advice", response_model=AdviceResponse)
def get_crypto_advice_ep(
    coin: Coin = Query(..., description="BTC / ETH / SOL"),
    model: LLModel = Query(..., description="GEMINI_FLASH / OPENAI_MINI"),
    username: str = Depends(auth_dep),
):
    prompt = build_prompt(coin)
    text, in_tokens, out_tokens, total = call_llm(model, prompt)

    price = quote(model)
    cost = estimate_cost(in_tokens, out_tokens, price)

    new_balance = deduct_balance(username, cost)
    if new_balance is False:
        raise HTTPException(status_code=402, detail="Insufficient balance")

    return {
        "reply": text,
        "coin": coin,
        "model": model,
        "price_per_1k": price,
        "usage_tokens": UsageTokens(
            in_tokens=in_tokens, out_tokens=out_tokens, total=total
        ),
        "estimated_cost_usd": round(cost, 6),
        "user_balance_usd": new_balance,
        "deducted_usd": round(cost, 6),
    }
