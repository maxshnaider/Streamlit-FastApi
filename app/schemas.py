from enum import StrEnum
from pydantic import BaseModel


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
