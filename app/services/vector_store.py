"""
向量存储服务：使用 sentence-transformers + ChromaDB 实现语义搜索
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


# 配置
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHROMA_DB_DIR = BASE_DIR / "chroma_db"
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

# 使用多语言模型（支持中英文）
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)

# 单例模式缓存
_model_cache: Optional[SentenceTransformer] = None
_chroma_client_cache: Optional[chromadb.ClientAPI] = None


def get_embedding_model() -> SentenceTransformer:
    """获取或创建 embedding 模型（单例）"""
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


def get_chroma_client() -> chromadb.ClientAPI:
    """获取或创建 ChromaDB 客户端（单例）"""
    global _chroma_client_cache
    if _chroma_client_cache is None:
        _chroma_client_cache = chromadb.PersistentClient(
            path=str(CHROMA_DB_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client_cache


def get_collection(collection_name: str = "audio_diary"):
    """获取或创建集合"""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
    )


def add_document(
    rid: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    collection_name: str = "audio_diary"
):
    """
    添加或更新文档到向量库
    
    Args:
        rid: 记录ID
        text: 文本内容（转写文本或总结）
        metadata: 元数据（文件名、创建时间等）
        collection_name: 集合名称
    """
    if not text or not text.strip():
        return
    
    model = get_embedding_model()
    collection = get_collection(collection_name)
    
    # 生成 embedding
    embedding = model.encode(text, convert_to_numpy=True).tolist()
    
    # 准备元数据
    meta = metadata or {}
    meta["rid"] = rid
    
    # Chroma 使用 upsert 自动处理新增或更新
    collection.upsert(
        ids=[rid],
        embeddings=[embedding],
        documents=[text],
        metadatas=[meta]
    )


def search_documents(
    query: str,
    n_results: int = 10,
    collection_name: str = "audio_diary"
) -> List[Dict[str, Any]]:
    """
    语义搜索文档
    
    Args:
        query: 搜索查询
        n_results: 返回结果数量
        collection_name: 集合名称
    
    Returns:
        搜索结果列表，每个结果包含: rid, text, metadata, distance
    """
    if not query or not query.strip():
        return []
    
    model = get_embedding_model()
    collection = get_collection(collection_name)
    
    # 生成查询 embedding
    query_embedding = model.encode(query, convert_to_numpy=True).tolist()
    
    # 执行搜索
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    # 格式化结果
    formatted_results = []
    if results and results.get("ids") and results["ids"][0]:
        for i, rid in enumerate(results["ids"][0]):
            formatted_results.append({
                "rid": rid,
                "text": results["documents"][0][i] if results.get("documents") else "",
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else 1.0
            })
    
    return formatted_results


def delete_document(rid: str, collection_name: str = "audio_diary"):
    """
    从向量库删除文档
    
    Args:
        rid: 记录ID
        collection_name: 集合名称
    """
    collection = get_collection(collection_name)
    try:
        collection.delete(ids=[rid])
    except Exception:
        pass  # 如果不存在则忽略


def rebuild_index(
    data_dir: Path,
    upload_dir: Path,
    collection_name: str = "audio_diary"
) -> Dict[str, int]:
    """
    重建索引：扫描所有现有的转写文本和总结，批量建立索引
    
    Args:
        data_dir: 数据目录（存放 .txt 和 .summary.txt）
        upload_dir: 上传目录（存放音频文件）
        collection_name: 集合名称
    
    Returns:
        统计信息：{"indexed": 已索引数量, "skipped": 跳过数量}
    """
    indexed = 0
    skipped = 0
    
    # 收集所有记录ID
    rids = set()
    for item in upload_dir.iterdir():
        if item.is_file() and not item.name.endswith('.proc.wav'):
            rids.add(item.stem)
    
    for rid in rids:
        transcript_file = data_dir / f"{rid}.txt"
        summary_file = data_dir / f"{rid}.summary.txt"
        
        # 优先使用总结，其次使用转写文本
        text = ""
        if summary_file.exists():
            text = summary_file.read_text(encoding="utf-8")
        elif transcript_file.exists():
            text = transcript_file.read_text(encoding="utf-8")
        
        if not text or not text.strip():
            skipped += 1
            continue
        
        # 读取元数据
        meta_file = data_dir / f"{rid}.meta.json"
        metadata = {}
        if meta_file.exists():
            try:
                metadata = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        # 添加到索引
        try:
            add_document(rid, text, metadata, collection_name)
            indexed += 1
        except Exception:
            skipped += 1
    
    return {"indexed": indexed, "skipped": skipped}
