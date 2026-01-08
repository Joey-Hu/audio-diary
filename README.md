# Audio Diary (demo)

一个开箱即用的音频日记/会议记录 Web 应用，支持自动转写、AI 总结和语义搜索。

## ✨ 核心功能

### 📤 音频上传与处理
- 支持多种音频格式：wav/mp3/m4a/aac/flac/ogg
- 后台异步处理，上传后立即返回
- 实时状态轮询，任务进度可视化

### 🎯 智能转写
- 使用 Faster-Whisper 本地转写（默认 `tiny` 模型）

### 🤖 AI 总结
- 结构化输出：标题、要点、行动项、结论
- 支持手动编辑与修正

### 🔍 语义搜索
- 本地向量数据库（ChromaDB）
- 多语言支持（中英文）
- 基于 sentence-transformers 的语义理解
- 相似度排序展示

### 📝 记录管理
- 历史记录列表（按时间倒序）
- 详情页：音频播放器 + 转写 + 总结
- 重新转写/重新总结/全部重跑
- 独立的总结编辑页面

## 🗂️ 目录结构
```
app/
  main.py               # FastAPI 应用
  services/
    transcribe.py       # 音频转写封装（faster-whisper）
    summarize.py        # 文本总结封装（OpenAI/DeepSeek 可选，本地算法兜底）
    vector_store.py     # 向量存储与语义搜索（ChromaDB + sentence-transformers）
templates/
  index.html            # 首页：上传与记录列表
  detail.html           # 详情页：播放器、转写、总结
  search.html           # 搜索页：语义搜索
  summary_edit.html     # 编辑页：编辑总结
static/
  style.css             # 样式
uploads/                # 音频文件存储目录（自动创建）
data/                   # 转写与总结文本存储目录（自动创建）
chroma_db/              # 向量数据库目录（自动创建）
requirements.txt        # 依赖
README.md               # 使用说明
TODO.md                 # 开发计划
```

## 🚀 快速开始

### 1. 安装依赖
```bash
# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）
```bash
# Whisper 配置
export WHISPER_MODEL=tiny          # 可选：base, small, medium, large-v3
export WHISPER_DEVICE=cpu          # 可选：cuda（需 GPU）
export WHISPER_COMPUTE_TYPE=int8   # GPU 可用：float16

# AI 总结配置（优先使用 DeepSeek）
export DEEPSEEK_API_KEY=your_key
export DEEPSEEK_BASE_URL=https://api.deepseek.com  # 可选
export DEEPSEEK_MODEL=deepseek-reasoner             # 可选

# 或使用 OpenAI
export OPENAI_API_KEY=your_key
export OPENAI_MODEL=gpt-4o-mini    # 可选

# Embedding 模型配置（可选）
export EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

### 3. 运行开发服务器
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. 访问应用
- 首页：`http://localhost:8000/`
- 搜索页：`http://localhost:8000/search`
- 健康检查：`http://localhost:8000/health`

### 5. 首次建立搜索索引（如有历史数据）
```bash
curl -X POST http://localhost:8000/admin/rebuild-index
```

## 🖥️ 本地部署（后台运行）

> 适用于在本机长期运行，不依赖 IDE/终端前台窗口。

### 启动服务
```bash
./scripts/start.sh
```

### 查看状态
```bash
./scripts/status.sh
```

### 查看日志
```bash
tail -f logs/server.out
tail -f logs/server.err
```

### 停止服务
```bash
./scripts/stop.sh
```

### 可选环境变量
- `PORT`：端口（默认 8000）
- `HOST`：监听地址（默认 0.0.0.0）
- `ENV_NAME`：conda 环境名（默认 audio-diary）
- `LOG_DIR`：日志目录（默认 logs）

## 📖 使用说明

### 上传音频
1. 在首页点击上传区域或拖拽音频文件
2. 点击"上传并处理"
3. 自动跳转到详情页，实时显示处理进度
4. 转写和总结完成后自动刷新展示结果

### 搜索记录
1. 点击首页右上角的"🔍 搜索"按钮
2. 输入搜索关键词（支持中英文、模糊语义搜索）
3. 查看相似度排序的搜索结果
4. 点击"查看详情"进入对应记录

### 编辑总结
1. 在详情页点击"编辑总结"按钮
2. 在独立编辑页面修改总结内容
3. 点击"保存总结"或"取消"返回详情页

### 重新处理
- **重新转写**：仅重新执行语音转写
- **重新总结**：基于现有转写重新生成总结
- **全部重跑**：从头执行转写和总结

## 📝 注意事项
- 首次使用某些 Whisper 模型会自动下载，耗时取决于网络
- 在 CPU 上使用 `tiny` 或 `base` 模型速度相对较快
- 长音频建议 GPU 或较大模型视情况使用
- OpenAI/DeepSeek 总结需要有效的 API Key
- 未配置 API Key 时会使用本地算法（效果较简洁）
- 首次使用语义搜索需要下载 embedding 模型（约 420MB）

## 📚 技术栈
- **后端**：FastAPI、Uvicorn
- **转写**：faster-whisper
- **总结**：OpenAI API / DeepSeek API / TextRank
- **搜索**：sentence-transformers、ChromaDB
- **前端**：原生 HTML/CSS/JS（无框架依赖）

## 🤝 贡献
欢迎提交 Issue 和 Pull Request！

## 📄 许可
MIT License
