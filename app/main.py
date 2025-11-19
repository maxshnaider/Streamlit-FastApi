from fastapi import FastAPI

from .db import init_db, create_user
from .routers import advisor

init_db()
create_user("admin", start_balance=0.05)
create_user("user", start_balance=0.05)

app = FastAPI(title="Gemini/OpenAI Bitcoin Advisor")

app.include_router(advisor.router)
