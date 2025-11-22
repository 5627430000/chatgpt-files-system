from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import urllib.parse
from typing import List
from document_processor import DocumentProcessor
from vector_db import VectorDatabase
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, AI_MODELS, DEFAULT_AI_MODEL
import requests
import json

# 初始化组件
app = FastAPI(title="文档ChatGPT系统")
document_processor = DocumentProcessor()
vector_db = VectorDatabase()


# AI客户端基类
class AIClient:
    def __init__(self, model_config: dict):
        self.model_config = model_config
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {model_config['api_key']}"
        }
        self.api_url = model_config["api_url"]
        self.model_name = model_config["model_name"]

    def generate_answer(self, question: str, context: str) -> str:
        """生成答案的通用方法，子类需要实现"""
        raise NotImplementedError("子类必须实现此方法")


# DeepSeek客户端
class DeepSeekClient(AIClient):
    def generate_answer(self, question: str, context: str) -> str:
        """使用DeepSeek生成答案"""
        prompt = f"""基于以下文档内容，回答用户的问题。如果文档中没有相关信息，请如实告知。
文档内容：
{context}
用户问题：{question}
请基于文档内容提供准确、有用的回答："""
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        try:
            print(f"正在调用DeepSeek API...")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            answer = result['choices'][0]['message']['content']
            print("DeepSeek API调用成功！")
            return answer
        except Exception as e:
            error_msg = f"生成回答时出错: {str(e)}"
            print(error_msg)
            return error_msg


# 智谱AI客户端
class ZhipuAIClient(AIClient):
    def generate_answer(self, question: str, context: str) -> str:
        """使用智谱AI生成答案"""
        prompt = f"""基于以下文档内容，回答用户的问题。如果文档中没有相关信息，请如实告知。
文档内容：
{context}
用户问题：{question}
请基于文档内容提供准确、有用的回答："""
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        try:
            print(f"正在调用智谱AI API...")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            # 智谱AI的响应格式可能不同，需要根据实际情况调整
            answer = result['choices'][0]['message']['content']
            print("智谱AI API调用成功！")
            return answer
        except Exception as e:
            error_msg = f"生成回答时出错: {str(e)}"
            print(error_msg)
            return error_msg


# AI客户端工厂
class AIClientFactory:
    @staticmethod
    def create_client(model_name: str) -> AIClient:
        if model_name not in AI_MODELS:
            raise ValueError(f"不支持的模型: {model_name}")

        model_config = AI_MODELS[model_name]
        if model_name == "deepseek":
            return DeepSeekClient(model_config)
        elif model_name == "zhipu":
            return ZhipuAIClient(model_config)
        else:
            raise ValueError(f"未实现的模型: {model_name}")


# 默认AI客户端
default_client = AIClientFactory.create_client(DEFAULT_AI_MODEL)

# CORS配置（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.get("/")
async def root():
    return {"message": "文档ChatGPT系统API服务运行中", "status": "正常"}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档接口"""
    try:
        print(f"收到文件上传请求: {file.filename}")
        # 解码URL编码的文件名
        原始文件名 = urllib.parse.unquote(file.filename)
        print(f"解码后的原始文件名: {原始文件名}")

        # 检查文件类型
        file_ext = os.path.splitext(原始文件名)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400,
                                detail=f"不支持的文件格式: {file_ext}，支持格式: {', '.join(ALLOWED_EXTENSIONS)}")

        # 保存文件（文件名用uuid）
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}{file_ext}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        print(f"文件保存到: {file_path}")

        # 处理文档
        chunks = document_processor.process_document(file_path, 原始文件名)
        # 添加到向量数据库
        vector_db.add_documents(chunks)

        return {
            "message": "文档上传成功",
            "filename": 原始文件名,
            "chunks_count": len(chunks),
            "document_id": file_id,
            "file_ext": file_ext  # 新增：返回文件扩展名
        }
    except Exception as e:
        print(f"处理文档时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理文档时出错: {str(e)}")


@app.post("/chat")
async def chat_with_document(question: str, model: str = DEFAULT_AI_MODEL):
    """与文档对话接口"""
    try:
        print(f"收到问题: {question}, 使用模型: {model}")
        if not question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")

        # 创建AI客户端
        try:
            ai_client = AIClientFactory.create_client(model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"不支持的AI模型: {model}")

        # 搜索相关文档片段
        search_results = vector_db.search(question, n_results=5)
        if not search_results:
            return {
                "answer": "抱歉，在已上传的文档中没有找到相关信息。请尝试上传相关文档或换一个问题。",
                "sources": [],
                "relevant_chunks": 0,
                "model_used": model
            }

        # 构建上下文
        context = "\n\n".join([f"来源: {result[1]['source']}\n内容: {result[0]}"
                               for result in search_results])
        print(f"使用 {len(search_results)} 个相关文档块生成回答...")

        # 生成回答
        answer = ai_client.generate_answer(question, context)

        # 提取来源信息
        sources = list(set([result[1]['source'] for result in search_results]))
        return {
            "answer": answer,
            "sources": sources,
            "relevant_chunks": len(search_results),
            "model_used": model
        }
    except Exception as e:
        print(f"生成回答时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成回答时出错: {str(e)}")


@app.get("/models")
async def get_available_models():
    """获取可用的AI模型列表"""
    return {
        "available_models": list(AI_MODELS.keys()),
        "default_model": DEFAULT_AI_MODEL
    }


@app.get("/documents")
async def get_documents():
    """获取所有已上传的文档列表"""
    try:
        documents = vector_db.get_all_documents()
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表时出错: {str(e)}")


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """删除指定文档"""
    try:
        vector_db.delete_document(filename)
        return {"message": f"文档 {filename} 已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档时出错: {str(e)}")


@app.get("/documents/{document_id}/content")
async def get_document_content(document_id: str):
    """获取指定文档的内容"""
    try:
        # 调试：打印原始输入的document_id
        print(f"\n===== 开始获取文档内容 =====")
        print(f"原始document_id: {document_id} (类型: {type(document_id)})")

        # 解码文档ID
        decoded_id = urllib.parse.unquote(document_id)
        print(f"解码后的document_id: {decoded_id} (类型: {type(decoded_id)})")

        # 查找对应的文件
        file_path = None
        file_ext = None
        print(f"开始在目录 {UPLOAD_FOLDER} 中查找文件...")

        # 调试：列出目录中所有文件，确认文件是否存在
        try:
            all_files = os.listdir(UPLOAD_FOLDER)
            print(f"上传目录文件列表: {all_files} (共 {len(all_files)} 个文件)")
        except Exception as e:
            print(f"读取上传目录失败: {str(e)} (可能是目录不存在或权限问题)")
            raise  # 继续抛出异常

        # 遍历文件查找匹配项
        for file in all_files:
            print(f"检查文件: {file} (是否以 {decoded_id} 开头: {file.startswith(decoded_id)})")
            if file.startswith(decoded_id):
                file_path = os.path.join(UPLOAD_FOLDER, file)
                file_ext = os.path.splitext(file)[1].lower()
                print(f"找到匹配文件: {file_path}, 扩展名: {file_ext}")
                break

        # 检查文件路径是否有效
        print(f"最终确定的file_path: {file_path}")
        if not file_path or not os.path.exists(file_path):
            print(
                f"文件不存在！file_path: {file_path}, 存在性检查: {os.path.exists(file_path) if file_path else '无路径'}")
            raise HTTPException(status_code=404, detail="文件不存在")

        # 检查文件是否可访问（权限检查）
        if not os.access(file_path, os.R_OK):
            print(f"没有读取权限！file_path: {file_path}")
            raise HTTPException(status_code=403, detail="没有文件读取权限")

        # 读取文件内容
        content = ""
        print(f"开始读取文件内容，类型: {file_ext}")
        try:
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(20000)  # 限制最大读取长度
                print(f"TXT文件读取完成，内容长度: {len(content)}")
            elif file_ext == '.pdf':
                content = document_processor.read_pdf(file_path)[:20000]
                print(f"PDF文件读取完成，内容长度: {len(content)}")
            elif file_ext == '.docx':
                content = document_processor.read_docx(file_path)[:20000]
                print(f"DOCX文件读取完成，内容长度: {len(content)}")
            else:
                print(f"不支持的文件类型: {file_ext}")
                raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")
        except Exception as read_err:
            print(f"读取文件内容时出错: {str(read_err)} (文件路径: {file_path})")
            raise  # 继续抛出异常

        # 准备返回结果
        result = {
            "filename": decoded_id,
            "content": content,
            "truncated": len(content) >= 20000,
            "file_ext": file_ext
        }
        print(f"文件内容获取成功，返回结果长度: {len(content)}")
        return result

    except HTTPException as he:
        # 已知HTTP异常（404/403等）
        print(f"HTTP异常: 状态码 {he.status_code}, 详情: {he.detail}")
        raise  # 保持原有异常抛出
    except Exception as e:
        # 未知异常
        print(f"获取文件内容失败（全局异常）: {str(e)} (类型: {type(e).__name__})")
        raise HTTPException(status_code=500, detail=f"获取文件内容失败: {str(e)}")
    finally:
        print(f"===== 结束获取文档内容 =====")


if __name__ == "__main__":
    import uvicorn

    print("启动文档ChatGPT系统后端服务...")
    uvicorn.run(app, host="0.0.0.0", port=8000)