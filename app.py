from enum import StrEnum
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from openai import OpenAI
import tiktoken
import os
from dotenv import load_dotenv

load_dotenv()

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


class AdviceResponse(BaseModel):
    reply: str
    coin: Coin
    model: LLModel
    price_per_1k: dict
    usage_tokens: dict
    estimated_cost_usd: float


PRICES = {
    LLModel.GEMINI_FLASH: {"in": 0.00010, "out": 0.00040},
    LLModel.OPENAI_MINI: {"in": 0.00015, "out": 0.00060},
}

EXPECTED_OUT_TOKENS = 90


def estimate_tokens_for_model(model: LLModel, prompt: str) -> int:
    if model == LLModel.OPENAI_MINI:
        enc = tiktoken.encoding_for_model("gpt-4o-mini")
    else:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(prompt))


@app.get("/estimate")
def estimate_cost(
    coin: Coin = Query(..., description="BTC / ETH / SOL"),
    model: LLModel = Query(..., description="GEMINI_FLASH / OPENAI_MINI"),
):
    prompt = (
        f"Give a short, practical trading tip for {coin} for today. "
        f"Max 3 sentences. No price guarantees; focus on risk management."
    )

    in_tokens = estimate_tokens_for_model(model, prompt)
    out_tokens = EXPECTED_OUT_TOKENS
    price = PRICES[model]
    cost = (in_tokens / 1000.0) * price["in"] + (out_tokens / 1000.0) * price["out"]

    return {
        "coin": coin,
        "model": model,
        "estimated_tokens": {
            "in": in_tokens,
            "out": out_tokens,
            "total": in_tokens + out_tokens,
        },
        "estimated_cost_usd": round(cost, 6),
    }


@app.get("/advice", response_model=AdviceResponse)
def get_crypto_advice(
    coin: Coin = Query(..., description="BTC / ETH / SOL"),
    model: LLModel = Query(..., description="GEMINI_FLASH / OPENAI_MINI"),
):
    prompt = (
        f"Give a short, practical trading tip for {coin} for today. "
        f"Max 3 sentences. No price guarantees; focus on risk management."
    )
    try:
        if model == LLModel.GEMINI_FLASH:
            g = genai.GenerativeModel(model.value)
            res = g.generate_content(prompt)

            text = (getattr(res, "text", None) or "").strip()
            if not text:
                raise ValueError("Empty response from Gemini")

            usage = getattr(res, "usage_metadata", None)
            if usage:
                in_tokens = getattr(usage, "prompt_token_count", 0) or 0
                out_tokens = getattr(usage, "candidates_token_count", 0) or 0
                total = getattr(usage, "total_token_count", in_tokens + out_tokens) or (
                    in_tokens + out_tokens
                )
            else:
                in_tokens = out_tokens = 0
                total = 0

        elif model == LLModel.OPENAI_MINI:
            res = openai_client.responses.create(model=model.value, input=prompt)

            text = (getattr(res, "output_text", "") or "").strip()
            if not text:
                raise ValueError("Empty response from OpenAI")

            u = getattr(res, "usage", None)
            in_tokens = int(getattr(u, "input_tokens", 0) or 0)
            out_tokens = int(getattr(u, "output_tokens", 0) or 0)
            total = int(
                getattr(u, "total_tokens", in_tokens + out_tokens)
                or (in_tokens + out_tokens)
            )

        else:
            raise HTTPException(status_code=400, detail="Unknown model")

        price = PRICES[model]
        cost = (in_tokens / 1000.0) * price["in"] + (out_tokens / 1000.0) * price["out"]

        return {
            "reply": text,
            "coin": coin,
            "model": model,
            "price_per_1k": price,
            "usage_tokens": {"in": in_tokens, "out": out_tokens, "total": total},
            "estimated_cost_usd": round(cost, 6),
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
