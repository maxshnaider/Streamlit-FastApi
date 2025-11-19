import os
from typing import Tuple

import google.generativeai as genai
from openai import OpenAI
import tiktoken
from dotenv import load_dotenv

from .schemas import Coin, LLModel, PricePer1K

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        raise ValueError("Unknown model")
