from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def home():
    return {"message": "хелоу"}

@app.get("/sum")
def get_sum(a: int, b: int):
    return {"result": a + b}

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
