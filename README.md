# Audio Diary (Python FastAPI)

一个开箱即用的音频上传、自动转写与AI总结的 Web 应用。

## 功能
- 上传音频文件（wav/mp3/m4a/aac/flac/ogg）
- 存储上传的录音文件到 `uploads/`
- 使用 Faster-Whisper 自动转写为文本（默认 `tiny` 模型、CPU）
- 总结转写文本：
  - 优先使用 DeepSeek（设置 `DEEPSEEK_API_KEY`，可选 `DEEPSEEK_BASE_URL` 与 `DEEPSEEK_MODEL`）
  - 其次使用 OpenAI（如设置 `OPENAI_API_KEY`）
  - 无法使用时，中文走 TextRank4zh，英文走 Sumy TextRank
- 浏览历史记录，查看详情页，包含音频播放器、转写与总结

## 目录结构
```
app/
  main.py               # FastAPI 应用
  services/
    transcribe.py       # 音频转写封装（faster-whisper）
    summarize.py        # 文本总结封装（OpenAI 可选，本地算法兜底）
templates/
  index.html            # 首页：上传与记录列表
  detail.html           # 详情页：播放器、转写、总结
static/
  style.css             # 简单样式
uploads/                # 音频文件存储目录（自动创建）
data/                   # 转写与总结文本存储目录（自动创建）
requirements.txt        # 依赖
README.md               # 使用说明
```

## 安装与运行
1. 创建并激活虚拟环境（推荐）：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. （可选）配置环境变量：
   - `WHISPER_MODEL`：默认 `tiny`（可选：base, small, medium, large-v3 等）
   - `WHISPER_DEVICE`：默认 `cpu`（如使用 GPU：`cuda`）
   - `WHISPER_COMPUTE_TYPE`：默认 `int8`（GPU 可用 `float16`）
   - `OPENAI_API_KEY`：设置后优先使用 OpenAI 总结
   - `OPENAI_MODEL`：默认 `gpt-4o-mini`

4. 运行开发服务器：
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. 打开浏览器访问：
   - 首页：`http://localhost:8000/`
   - 健康检查：`http://localhost:8000/health`

## 使用说明
- 在首页上传音频文件，系统会自动执行：保存文件 -> 语音转写 -> 总结文本 -> 跳转到详情页展示结果。
- 历史记录列表会展示是否已有转写与总结，可点击进入详情查看。

## 注意事项
- 首次使用某些 Whisper 模型会自动下载，耗时与网络相关。
- 在 CPU 上使用 `tiny` 或 `base` 模型速度相对较快；长音频建议 GPU 或较大模型视情况使用。
- OpenAI 总结需要有效的 API Key；未配置时会使用本地算法（效果较简洁）。

## 许可
MIT
