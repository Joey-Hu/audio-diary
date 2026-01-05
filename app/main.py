import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services.transcribe import transcribe_audio
from app.services.summarize import summarize_text

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Audio Diary - 上传、转写与总结")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def list_records() -> List[dict]:
    records = []
    for item in UPLOAD_DIR.iterdir():
        if item.is_file():
            rid = item.stem
            transcript_file = DATA_DIR / f"{rid}.txt"
            summary_file = DATA_DIR / f"{rid}.summary.txt"
            records.append({
                "id": rid,
                "filename": item.name,
                "audio_url": f"/uploads/{item.name}",
                "has_transcript": transcript_file.exists(),
                "has_summary": summary_file.exists(),
            })
    return sorted(records, key=lambda r: r["id"], reverse=True)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "records": list_records()})


@app.get("/detail/{rid}", response_class=HTMLResponse)
async def detail(request: Request, rid: str):
    audio_file = next((p for p in UPLOAD_DIR.glob(f"{rid}.*")), None)
    if not audio_file:
        return HTMLResponse("记录不存在", status_code=404)
    transcript_file = DATA_DIR / f"{rid}.txt"
    summary_file = DATA_DIR / f"{rid}.summary.txt"
    transcript = transcript_file.read_text(encoding="utf-8") if transcript_file.exists() else ""
    summary = summary_file.read_text(encoding="utf-8") if summary_file.exists() else ""
    return templates.TemplateResponse("detail.html", {
        "request": request,
        "rid": rid,
        "filename": audio_file.name,
        "audio_url": f"/uploads/{audio_file.name}",
        "transcript": transcript,
        "summary": summary,
    })


@app.post("/upload")
async def upload_audio(request: Request, file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"]:
        return HTMLResponse("仅支持音频文件: wav/mp3/m4a/aac/flac/ogg", status_code=400)
    rid = uuid.uuid4().hex
    target = UPLOAD_DIR / f"{rid}{suffix}"
    try:
        with open(target, "wb") as f:
            f.write(await file.read())
        transcript = transcribe_audio(str(target))
        (DATA_DIR / f"{rid}.txt").write_text(transcript, encoding="utf-8")
        summary = summarize_text(transcript)
        (DATA_DIR / f"{rid}.summary.txt").write_text(summary, encoding="utf-8")
        return RedirectResponse(url=f"/detail/{rid}", status_code=303)
    except Exception as e:
        # 写入错误信息，方便后续排查
        (DATA_DIR / f"{rid}.error.txt").write_text(str(e), encoding="utf-8")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "rid": rid,
            "filename": Path(file.filename).name,
            "error": str(e),
        }, status_code=500)


# Expose uploads statically
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
