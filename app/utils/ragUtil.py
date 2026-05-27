from abc import ABC, abstractmethod
from collections.abc import Sequence
import os
import tempfile
import traceback
import importlib
from dotenv import load_dotenv
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document
from llama_index.core.storage import StorageContext
from llama_index.vector_stores.milvus import MilvusVectorStore
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.env_util import require_env
from utils.llms import embedder_model
from utils.picUtil import get_text_from_pic

load_dotenv()

# 与 rag_context 中 persist 目录一致。若要用库默认目录可改为：
# from llama_index.core.storage.storage_context import DEFAULT_PERSIST_DIR  # 值为 "./storage"
DEFAULT_PERSIST_DIR = "RAG/data/index"


def _ensure_stdlib_xml() -> None:
    """确保使用标准库 xml，避免三方 xml 包遮蔽导致 PDF 解析失败。"""
    try:
        stdlib_path = str(Path(os.__file__).resolve().parent)
        xml_module = importlib.import_module("xml")
        xml_file = getattr(xml_module, "__file__", "") or ""
        if "site-packages" in xml_file:
            sys.modules.pop("xml", None)
            if stdlib_path not in sys.path:
                sys.path.insert(0, stdlib_path)
            importlib.import_module("xml.dom.expatbuilder")
    except Exception:
        # 失败时交给下游读取逻辑抛出更明确异常
        pass


class RAGBASE(ABC):
    def __init__(self, files: list[str]):
        self.files = files
        
        
    # 加载数据
    @abstractmethod
    def load_file(self) -> Sequence[Document] | None:
        """加载数据，因为加载的方式有多种 （文件、目录、数据库），所以需要抽象出一个方法来加载数据,待子类去实现 --》documents
        """
        raise NotImplementedError
        
    # 构建本地索引
    def create_local_index(self):
        """构建本地索引
        """
        
        # 加载数据 得到documents
        docs = self.load_file()
        if docs is None:
            raise ValueError("数据加载失败")
        # 构建索引
        index = VectorStoreIndex.from_documents(docs, show_progress=True)
        # 持久化索引
        index.storage_context.persist(persist_dir=DEFAULT_PERSIST_DIR)
        
        return  index
    # 加载本地索引
    @staticmethod
    def load_local_index():
        """加载本地索引
        """
        # 加载索引
        index = load_index_from_storage(StorageContext.from_defaults(persist_dir=DEFAULT_PERSIST_DIR))
        return index
    
    # 创建远程索引
    async def create_remote_index(self,collection_name="default"):
        """创建远程索引
        """
        
        # 加载数据
        data = self.load_file()
        
        # 创建一个分割器
        node_splitter = SentenceSplitter.from_defaults(separator="。",chunk_size=1024,chunk_overlap=20)
        # 切分
        nodes = node_splitter.get_nodes_from_documents(documents=data,show_progress=True) if data else []
        # 向量数据库存储对象
        vector_store = MilvusVectorStore(
            uri=require_env("milvus_uri"),
            collection_name=collection_name,
            dim =1024, #向量数据库的维度
            overwrite=True
        ) 
        
        # StorageContext存储上下文管理器，用于统一管理向量存储
        # from_defaults 通过默认配置创建StorageContext对象
        stroage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # 将节点数据转化为向量并存入 milvus,同时创建了一个可查询的索引
        index = VectorStoreIndex(nodes, storage_context=stroage_context)
        return  index
    # 加载远程索引
    @staticmethod
    def load_remote_index(collection_name="default"):
        """加载远程索引
        """
        # 加载索引
        # 向量数据库存储对象
        vector_store = MilvusVectorStore(
            uri=require_env("milvus_uri"),
            collection_name=collection_name,
            dim =1024, #向量数据库的维度
            overwrite=False
        ) 
        
        # 从已有的MilvusVectorStore 加载索引
        return VectorStoreIndex.from_vector_store(vector_store=vector_store)
        
    
    
class NormalDocumentRAG(RAGBASE):
    def load_file(self) -> list[Document]:
        """加载文件
        """
        _ensure_stdlib_xml()
        docs = []
        for file in self.files:
            # 获取文件名
            file_name = os.path.basename(file)
            # 获取文件扩展名
            file_extension = os.path.splitext(file_name.lower())[1]
            
            # 如果是图片
            if file_extension in [".jpg", ".png"]:
                contents = get_text_from_pic(file)
                with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', encoding='utf-8') as temp_file:
                    temp_file.write(contents)
                    temp_file.flush()
                    
                    # 返回的是一个 list[document]对象
                    data = SimpleDirectoryReader(input_files=[temp_file.name]).load_data()
                    
                    doc = Document(text="\n\n".join([d.text for d in data[::2]]), metadata={"path": file})
                    docs.append(doc)
            elif file_extension in [".pdf", ".docx", ".doc", ".txt"]: # 如果是文件
                try:
                    data = SimpleDirectoryReader(input_files=[file]).load_data()
                    docs.extend(data)
                except Exception as e:
                    # 打印根因，避免只看到 RetryError 包装信息
                    print(f"加载文件失败: {file}, error={e!r}")
                    traceback.print_exc()
        return docs

if __name__ == "__main__":
    docs = NormalDocumentRAG(["RAG/data/测试商品.jpg"]).load_file()
    print(docs)