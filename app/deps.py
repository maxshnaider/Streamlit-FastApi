from fastapi import Query, HTTPException

AUTH = {"admin": "admin", "user": "user"}


def auth_dep(
    username: str = Query(..., description="account username (admin/user)"),
    password: str = Query(..., description="password (admin/user)"),
) -> str:
    if username not in AUTH or AUTH[username] != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return username
