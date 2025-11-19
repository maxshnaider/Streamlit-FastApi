from fastapi import APIRouter, Depends, Form, HTTPException, Query

from ..schemas import Coin, LLModel, AdviceResponse, UsageTokens
from ..db import get_balance, deduct_balance, get_user_info
from ..deps import auth_dep, AUTH
from ..services import (
    build_prompt,
    quote,
    estimate_tokens_for_model,
    estimate_cost,
    call_llm,
    EXPECTED_OUT_TOKENS,
)

router = APIRouter(tags=["advisor"])


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username not in AUTH or AUTH[username] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "balance": round(get_balance(username), 6)}


@router.get("/user")
def get_user(username: str = Depends(auth_dep)):
    info = get_user_info(username)
    if not info:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": username, **info}


@router.get("/estimate")
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


@router.get("/advice", response_model=AdviceResponse)
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
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            total=total,
        ),
        "estimated_cost_usd": round(cost, 6),
        "user_balance_usd": new_balance,
        "deducted_usd": round(cost, 6),
    }
