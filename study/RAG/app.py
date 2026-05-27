import os
import tempfile
from llama_index.core.chat_engine.types import ChatMode
import streamlit as st
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.llms.deepseek import DeepSeek
from llama_index.embeddings.ollama import OllamaEmbedding
from utils.milvusUtil import list_collections
from utils.ragUtil import NormalDocumentRAG
from utils.llms import ds_llm, embedder_model

# 执行页面级基础配置，需放在前面以保证生效。
st.set_page_config(
    # 配置浏览器标签页标题。
    page_title="Anson智能问答助手",
    # 配置页面图标为机器人。
    page_icon=":robot:",
    # 配置页面布局为宽屏。
    layout="wide",
)

# # 设置主标题，展示应用名称。
# st.title("Anson智能问答助手")
# # 设置副标题，告知当前是入门版问答页。
# st.markdown("> 基于 Streamlit + LlamaIndex + DeepSeek 的最小可用问答页面")




def init_chat_engine():
    """始终返回可用的聊天引擎；文档索引路径失败时回退为普通对话。"""
    try:
        if st.session_state.get("document_index"):
            # chat_mode=ChatMode.CONTEXT 表示使用上下文模式，聊天引擎会基于索引中的文档内容来回答问题，而不仅仅依赖于大模型
            return st.session_state.document_index.as_chat_engine(chat_mode=ChatMode.CONTEXT)
        elif st.session_state.chat_mode == "知识库聊天模式" and st.session_state.knowledge_collection_name:
            # 加载远程索引
            index = NormalDocumentRAG.load_remote_index(st.session_state.knowledge_collection_name)
            return index.as_chat_engine(chat_mode=ChatMode.CONTEXT)
        else:
            chat_engine = SimpleChatEngine.from_defaults() # 普通对话模式
            return chat_engine
    except Exception as e:
        st.warning(f"聊天引擎初始化失败: {e}")
        return SimpleChatEngine.from_defaults(llm=ds_llm)


def render_rag_selector():
    """
    渲染知识库选择器
    """
    st.subheader("选择知识库")
    try:
        collections = list_collections()
        if not collections:
            st.warning("没有可用的知识库,请先创建")
            st.session_state.knowledge_collection_name = None
            return  
        kb_options=['请选择知识库']+collections
        
        def on_kb_change():
            selectd = st.session_state.kb_selector
            st.session_state.knowledge_collection_name = None if selectd == '请选择知识库' else selectd

        
        current_index = 0
        if st.session_state.knowledge_collection_name in kb_options:
            current_index = kb_options.index(st.session_state.knowledge_collection_name)
        
        st.selectbox(
            "请选择知识库", 
            kb_options, 
            on_change=on_kb_change,  # 设置选项改变时的回调函数，当选择不同的知识库选项时，会自动调用 on_kb_change 函数
            key="kb_selector",
            index=current_index, 
            help="请选择不同的知识库，体验不同的功能")
        if st.session_state.knowledge_collection_name:
            st.info(f"已选择知识库: {st.session_state.knowledge_collection_name}")  
    except Exception as e:
        st.error(f"无法获取知识库: {e}")
        return None

def main():
    
    # st.session_state 创建一个会话状态，用于保存用户输入的参数，以及中间结果，如聊天记录
    if "document_index" not in st.session_state:
        st.session_state.document_index = None
    
    if "chat_mode" not in st.session_state:
        st.session_state.chat_mode = "普通聊天模式"
        
    if "knowledge_collection_name" not in st.session_state:
        st.session_state.knowledge_collection_name = None
        
    if "uploaded_files_signature" not in st.session_state:
        st.session_state.uploaded_files_signature = None
        
    
    st.title("Anson智能问答助手")
    st.markdown("> 基于 Streamlit + LlamaIndex + DeepSeek 的最小可用问答页面")
    
    
    # 初始化llm和embedder
    Settings.llm = ds_llm
    Settings.embed_model = embedder_model
   
    
    
    # st.sidebar 创建一个侧边栏区域，用于放置文件上传、模式切换、清除聊天记录
    with st.sidebar:
        # 设置章节标题，级别低于title
        st.header("聊天模式")
        
        chat_modes = ["普通聊天模式", "文档问答模式", "知识库聊天模式"]
        select_mode = st.selectbox(
            "请选择聊天模式", 
            chat_modes, 
            index=chat_modes.index(st.session_state.chat_mode), 
            help="请选择不同的聊天模式，体验不同的功能") 
        
        if select_mode != st.session_state.chat_mode:
            st.session_state.chat_mode = select_mode
            st.rerun()
        
        # 根据不同的模式来渲染不同的控件
        if st.session_state.chat_mode == "文档问答模式":
            st.subheader("上传文档")
            uploaded_files = st.file_uploader("上传文件",
                                          type=["pdf","txt","md","docx","excel","jpg","png"],
                                          accept_multiple_files=True,
                                          help="上传文档后可以基于文档内容问答")
        
        elif st.session_state.chat_mode == "知识库聊天模式":
            render_rag_selector()
            uploaded_files=[]
        else:
            uploaded_files=[]
        
    if uploaded_files  and st.session_state.chat_mode == "文档问答模式":
        current_signature = tuple(
            (f.name, f.size, hash(f.getvalue())) for f in uploaded_files
        )
        if st.session_state.uploaded_files_signature == current_signature:
            # 文件未变化，跳过重复向量化
            pass
        else:
            st.session_state.uploaded_files_signature = current_signature
            with st.spinner("文档处理中..."):
                
                #创建一个临时目录，用于存放临时文件，退出with语句块时，会自动删除整个临时目录及其内容
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    file_paths = []
                    for upload_file in uploaded_files:
                        file_path = os.path.join(temp_dir, upload_file.name)
                        with open(file_path, "wb") as f:
                            f.write(upload_file.getbuffer())
                        file_paths.append(file_path)
                    
                    # 创建文档索引
                    document_rag = NormalDocumentRAG(file_paths)
                    index = document_rag.create_local_index()
                    st.session_state.document_index = index
                    st.success(f"已成功处理{len(file_paths)}个文件")

    
    if prompt := st.chat_input("请输入你的问题"):
            with st.chat_message("user"):
                st.markdown(prompt) #显示用户输入的问题
                
            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    try:
                        # 获取聊天引擎    
                        chat_engine = init_chat_engine()
                        
                        # 使用流式输出
                        response = chat_engine.stream_chat(prompt) 
                        
                        # st_empty() 返回一个占位符，用于显示流式输出
                        message_placeholder = st.empty()
                        
                        full_response = ""
                        for token in response.response_gen:
                            full_response += token
                            message_placeholder.markdown(full_response)
                            
                    except Exception as e:
                        st.error(f"聊天失败: {e}")
       
    



if __name__ == "__main__":
    main()
