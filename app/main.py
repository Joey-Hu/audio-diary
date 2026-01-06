import os
import uuid
from pathlib import Path
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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


def normalize_rid(rid: str) -> str:
    # 避免某些客户端/脚本拼接时把分号等带进路径参数
    return rid.strip().strip(";")



def _status_path(rid: str) -> Path:
    rid = normalize_rid(rid)
    return DATA_DIR / f"{rid}.status.json"


def read_status(rid: str) -> Dict[str, Any]:
    rid = normalize_rid(rid)
    p = _status_path(rid)
    if not p.exists():
        return {"rid": rid, "state": "idle", "updated_at": None}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"rid": rid, "state": "error", "error": "Invalid status file", "updated_at": None}


def write_status(
    rid: str,
    state: str,
    *,
    mode: Optional[str] = None,
    error: Optional[str] = None,
    message: Optional[str] = None,
    started_at: Optional[int] = None,
) -> Dict[str, Any]:
    rid = normalize_rid(rid)
    now = int(time.time())
    payload: Dict[str, Any] = {
        "rid": rid,
        "state": state,
        "mode": mode,
        "message": message,
        "error": error,
        "started_at": started_at,
        "updated_at": now,
    }
    _status_path(rid).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def list_records() -> List[dict]:
    records: List[Dict[str, Any]] = []

    # 先收集原始数据
    for item in UPLOAD_DIR.iterdir():
        if not item.is_file():
            continue

        # 忽略转写预处理产生的临时文件（历史遗留）
        if item.name.endswith('.proc.wav'):
            continue

        rid = item.stem
        transcript_file = DATA_DIR / f"{rid}.txt"
        summary_file = DATA_DIR / f"{rid}.summary.txt"
        st = read_status(rid)

        # 读取 meta（兼容旧数据）
        meta_path = DATA_DIR / f"{rid}.meta.json"
        original_filename = item.name
        created_at = int(item.stat().st_mtime)
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                original_filename = meta.get("original_filename") or original_filename
                created_at = int(meta.get("created_at") or created_at)
            except Exception:
                pass

        created_at_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(created_at))
        records.append({
            "id": rid,
            "created_at": created_at,
            "created_at_str": created_at_str,
            "original_filename": original_filename,
            "filename": item.name,  # 实际存储文件名（rid.ext）
            "audio_url": f"/uploads/{item.name}",
            "has_transcript": transcript_file.exists(),
            "has_summary": summary_file.exists(),
            "task_state": st.get("state", "idle"),
            "task_error": st.get("error", ""),
        })

    # 对“用户上传文件名”做同名去重展示：name, name(1), name(2)...
    name_counter: Dict[str, int] = {}
    for r in sorted(records, key=lambda x: x["created_at"], reverse=True):
        base = r["original_filename"]
        idx = name_counter.get(base, 0)
        if idx == 0:
            r["display_filename"] = base
        else:
            r["display_filename"] = f"{base}（{idx}）"
        name_counter[base] = idx + 1

    return sorted(records, key=lambda r: r["created_at"], reverse=True)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "records": list_records()})


@app.get("/detail/{rid}", response_class=HTMLResponse)
async def detail(request: Request, rid: str):
    rid = normalize_rid(rid)
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
        "status": read_status(rid),
    })


@app.post("/upload")
async def upload_audio(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"]:
        return HTMLResponse("仅支持音频文件: wav/mp3/m4a/aac/flac/ogg", status_code=400)

    rid = uuid.uuid4().hex
    target = UPLOAD_DIR / f"{rid}{suffix}"

    try:
        with open(target, "wb") as f:
            f.write(await file.read())

        # 保存元信息（用户原始文件名、创建时间）
        meta = {
            "rid": rid,
            "original_filename": Path(file.filename).name,
            "created_at": int(time.time()),
        }
        (DATA_DIR / f"{rid}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        # 写入 queued 并投递后台任务（转写 + 总结）
        write_status(rid, "queued", mode="all", message="queued")
        background_tasks.add_task(_run_task, rid, "all")

        # 立即跳转到详情页（由前端轮询状态）
        return RedirectResponse(url=f"/detail/{rid}", status_code=303)
    except Exception as e:
        # 上传保存阶段失败，写 error 文件并返回错误页
        (DATA_DIR / f"{rid}.error.txt").write_text(str(e), encoding="utf-8")
        write_status(rid, "error", mode="all", error=str(e), message="upload failed")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "rid": rid,
                "filename": Path(file.filename).name,
                "error": str(e),
            },
            status_code=500,
        )


@app.post("/detail/{rid}/summary")
async def update_summary(rid: str, summary: Optional[str] = Form(None)):
    rid = normalize_rid(rid)
    # 校验记录存在（至少音频文件存在）
    audio_file = next((p for p in UPLOAD_DIR.glob(f"{rid}.*")), None)
    if not audio_file:
        return HTMLResponse("记录不存在", status_code=404)

    (DATA_DIR / f"{rid}.summary.txt").write_text(summary or "", encoding="utf-8")
    return RedirectResponse(url=f"/detail/{rid}", status_code=303)


@app.post("/delete/{rid}")
async def delete_record(rid: str):
    rid = normalize_rid(rid)
    # 删除上传音频
    removed = False
    for p in UPLOAD_DIR.glob(f"{rid}.*"):
        try:
            p.unlink()
            removed = True
        except Exception:
            pass
    # 删除转写与总结与错误文件
    for suffix in [".txt", ".summary.txt", ".error.txt"]:
        f = DATA_DIR / f"{rid}{suffix}"
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass
    # 重定向回首页
    return RedirectResponse(url="/", status_code=303)


# Expose uploads statically
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/status/{rid}")
async def status(rid: str):
    return JSONResponse(read_status(rid))


def _run_task(rid: str, mode: str):
    rid = normalize_rid(rid)
    # mode: transcribe | summarize | all
    audio_file = next((p for p in UPLOAD_DIR.glob(f"{rid}.*")), None)
    if not audio_file:
        write_status(rid, "error", mode=mode, error="record_not_found")
        return

    started_at = int(time.time())
    try:
        write_status(rid, "running", mode=mode, started_at=started_at, message="task started")

        transcript_file = DATA_DIR / f"{rid}.txt"
        summary_file = DATA_DIR / f"{rid}.summary.txt"

        transcript: str = transcript_file.read_text(encoding="utf-8") if transcript_file.exists() else ""

        if mode in ("transcribe", "all"):
            write_status(rid, "transcribing", mode=mode, started_at=started_at, message="transcribing")
            transcript = transcribe_audio(str(audio_file))
            transcript_file.write_text(transcript, encoding="utf-8")

        if mode in ("summarize", "all"):
            write_status(rid, "summarizing", mode=mode, started_at=started_at, message="summarizing (timeout=180s)")

            # 对 summarize 增加超时保护，避免任务卡死
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(summarize_text, transcript)
                try:
                    summary = fut.result(timeout=180)
                except FuturesTimeoutError:
                    write_status(
                        rid,
                        "error",
                        mode=mode,
                        started_at=started_at,
                        error="summarize_timeout",
                        message="summarize timeout (180s)",
                    )
                    return

            summary_file.write_text(summary, encoding="utf-8")

        write_status(rid, "done", mode=mode, started_at=started_at, message="done")
    except Exception as e:
        write_status(rid, "error", mode=mode, started_at=started_at, error=str(e), message="error")


@app.post("/tasks/{rid}/rerun")
async def rerun_task(rid: str, background_tasks: BackgroundTasks, mode: str = Form("all")):
    rid = normalize_rid(rid)
    if mode not in {"transcribe", "summarize", "all"}:
        return HTMLResponse("mode must be transcribe/summarize/all", status_code=400)

    # 立即写入 queued 并投递后台任务
    write_status(rid, "queued", mode=mode, message="queued")
    background_tasks.add_task(_run_task, rid, mode)

    # 立刻回详情页，前端轮询 status
    return RedirectResponse(url=f"/detail/{rid}", status_code=303)


@app.get("/health")
async def health():
    return {"status": "ok"}
