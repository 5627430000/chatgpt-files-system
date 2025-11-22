import os

# 多AI模型配置（只保留DeepSeek和Zhipu）
AI_MODELS = {
    "deepseek": {
        "api_key": "sk-a6bf826f0a4246a482ed44e778422bde",  # 请替换为您的DeepSeek API Key
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model_name": "deepseek-chat"
    },
    "zhipu": {
        "api_key": "c18dbc4af15f49c780949841ee24b199.gKAxUxG1EiuoAEi2",  # 🔑 替换为您的智谱AI API Key
        "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model_name": "glm-4"
    }
}

# 默认AI模型
DEFAULT_AI_MODEL = "deepseek"

# 向量数据库配置
VECTOR_DB_PATH = "./chroma_db"
EMBEDDING_MODEL = "BAAI/bge-small-zh"  # 中文优化的embedding模型

# 文档处理配置
CHUNK_SIZE = 500  # 文本块大小
CHUNK_OVERLAP = 50  # 文本块重叠大小

# 文件上传配置
UPLOAD_FOLDER = "./data/uploaded_files"
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VECTOR_DB_PATH, exist_ok=True)