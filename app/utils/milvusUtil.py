import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from pymilvus import MilvusClient

# 直接 `python RAG/utils/milvusUtil.py` 时，需把 RAG 根目录加入 path，才能 `import utils`。
_RAG_ROOT = Path(__file__).resolve().parent.parent
if str(_RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(_RAG_ROOT))
from utils.env_util import require_env

load_dotenv(_RAG_ROOT.parent / ".env")




client = MilvusClient(
    uri=require_env("milvus_uri"),
)


def list_collections() -> Any:
    """列出所有集合名称。"""
    return client.list_collections()


def create_collection(collection_name: str, **kwargs: Any) -> Any:
    """创建集合（参数与 `MilvusClient.create_collection` 一致）。"""
    return client.create_collection(collection_name, **kwargs)


if __name__ == "__main__":
    print(len(list_collections()))




