from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)

DEFAULT_PERSIST_DIR = "RAG/data/index"
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.llms.deepseek import DeepSeek

from utils.ragUtil import RAGBASE
# # documents = SimpleDirectoryReader(input_files=["RAG/data/PUR_PRD_v1.pdf"]).load_data()
# # # print(documents)

# # # # 加载多个文件
# documents = SimpleDirectoryReader(input_dir="RAG/data").load_data()
# # # print(len(documents))


# # # Node（节点）：是文档的抽象，包含文档的文本内容和元数据
# node_splitter = SentenceSplitter.from_defaults(separator=".",chunk_size=1024,chunk_overlap=10)

# nodes = node_splitter.get_nodes_from_documents(documents,show_progress=True)

# print(len(nodes))
# # print(nodes)



from llama_index.embeddings.ollama import OllamaEmbedding

ollama_embedding = OllamaEmbedding(
    model_name="qwen3-embedding:0.6b",
    base_url="http://149.28.114.71:11434"
)

Settings.embed_model = ollama_embedding
# # 构建索引
# embedder = DashScopeEmbedding(
#     model_name="text-embedding-v4",
#     api_key="sk-438118fbe21244fe8649f37e77ebf8a6",
#     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
# )

# Settings.embed_model = embedder

documents = SimpleDirectoryReader(input_files=["RAG/data/PUR_PRD_v1.pdf"]).load_data()


# 从文档列表构建向量索引，并显示处理进度(默认会转化为节点)
index = VectorStoreIndex.from_documents(documents,show_progress=True) 

# 将索引持久化到本地，以便后续加载复用，避免重复构建
index.storage_context.persist(persist_dir="RAG/data/index") 

print(index)



# 加载索引 -相当于连接数据库
index = load_index_from_storage(StorageContext.from_defaults(persist_dir=DEFAULT_PERSIST_DIR))
print(index)


# as_retriever
r = index.as_retriever(similarity_top_k=2) #用向量相似度从索引里检索时，只取与当前问题最相近的 2 条文本块（node/chunk） 作为上下文，再交给后面的 LLM 生成答案。

# 先会把文字转化为数字(向量数据)，然后到索引中做相似匹配，不会和大模型交互
data = r.retrieve("功能性需求是什么")
print(data)


# as_query_engine
llm = DeepSeek(model="deepseek-reasoner", api_key="sk-36eca0b473084e848bcff12ee6035cc5")
Settings.llm = llm


q = index.as_query_engine()
data = q.query("功能性需求是什么")
print(data)



