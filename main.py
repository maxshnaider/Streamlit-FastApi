from fastapi import FastAPI

app = FastAPI()


@app.get("/sum")
def get_sum(a: int, b: int):
    result = a + b
    return {"result": result}
