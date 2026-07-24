import os
import sys

API_DIR = os.path.dirname(os.path.abspath(__file__))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from evaluate import run_evaluation  # noqa: E402
from generate import run_generation  # noqa: E402

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT_DIR = os.path.dirname(API_DIR)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.post("/api/evaluate")
async def evaluate(request: Request):
    raw_body = (await request.body()).decode("utf-8")
    status, payload = run_evaluation(raw_body)
    return JSONResponse(payload, status_code=status, headers={"Cache-Control": "no-store"})


@app.get("/api/evaluate")
async def evaluate_get():
    return JSONResponse(
        {"error": "GET은 지원하지 않습니다. POST로 요청해 주세요."}, status_code=405
    )


@app.options("/api/evaluate")
async def evaluate_options():
    return JSONResponse({"ok": True})


@app.post("/api/generate")
async def generate(request: Request):
    raw_body = (await request.body()).decode("utf-8")
    status, payload = run_generation(raw_body)
    return JSONResponse(payload, status_code=status, headers={"Cache-Control": "no-store"})


@app.get("/api/generate")
async def generate_get():
    return JSONResponse(
        {"error": "GET은 지원하지 않습니다. POST로 요청해 주세요."}, status_code=405
    )


@app.options("/api/generate")
async def generate_options():
    return JSONResponse({"ok": True})


app.mount("/", StaticFiles(directory=ROOT_DIR, html=True), name="static")
