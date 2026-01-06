# Audio Diary - 开发 TODO

> 目标：逐步把 demo 提升为可长期使用的音频日记/会议记录工具。

## Roadmap（按实现顺序）

### 1) 支持“手动编辑/修正总结”（当前优先）
- [x] 详情页增加总结编辑区（只编辑 Summary，不编辑 Transcript）
- [x] 新增保存接口：保存到 `data/{rid}.summary.txt`
- [x] 保存成功后 **重定向回详情页** `/detail/{rid}`
- [ ] （优化）将“编辑总结”改为独立编辑页（避免详情页过长）
  - [ ] 详情页点击【编辑总结】按钮，跳转到 `/detail/{rid}/summary/edit`
  - [ ] 在编辑页进行编辑与保存（保存到 `data/{rid}.summary.txt`）
  - [ ] 保存成功后跳转回详情页 `/detail/{rid}` 并展示最新总结
  - [ ] （可选）保存后自动关闭窗口：仅在 `window.open` 打开新窗口时可用（否则用重定向替代）
- [ ] （可选）保存时记录编辑时间到 `data/{rid}.meta.json`

### 2) “重新总结 / 重新转写”按钮（后台任务队列雏形）
- [x] 详情页增加“重新转写 / 重新总结 / 全部重跑”按钮
- [x] 后端新增 rerun 投递接口：`POST /tasks/{rid}/rerun`（`mode=transcribe|summarize|all`），覆盖写回 `data/{rid}.txt` 与 `data/{rid}.summary.txt`
- [x] 新增状态查询接口：`GET /status/{rid}`（读取 `data/{rid}.status.json`）
- [x] 详情页轮询状态，任务完成后自动刷新展示结果
- [x] 总结阶段增加超时保护：180s（超时写入 `state=error` / `error=summarize_timeout`）
- [ ] （可选）记录更完整的任务日志/耗时统计到 `status.json`

### 3) 后台任务队列：上传后立即返回，前端轮询进度
- [x] `/upload` 改为：保存文件后立刻返回（重定向到详情页）
- [x] 后台任务执行转写/总结，写入进度文件：`data/{rid}.status.json`
- [x] 详情页轮询状态并刷新 UI（复用第 2 项机制）

### 4) 全局搜索（语义搜索）：向量库 + embedding
- [ ] Embedding 方案：优先 **本地**（`sentence-transformers`）
- [ ] 向量库：优先 **Chroma**（本地持久化，便于开箱即用）
- [ ] 上传/重跑后增量更新索引
- [ ] 提供全局搜索页：query → embedding → 相似度检索 → 展示结果（记录 + 片段）
- [ ] 提供“首次建库”能力：扫描现有 `data/*.txt` 初始化索引
