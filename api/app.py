from fastapi import FastAPI, Path

app = FastAPI()


@app.get("/")
def home():
    return {"Home": "Page"}
