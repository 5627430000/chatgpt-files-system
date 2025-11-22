import chromadb
from sentence_transformers import SentenceTransformer
import os
import urllib.parse
from typing import List, Tuple, Dict
from config import VECTOR_DB_PATH, EMBEDDING_MODEL


class VectorDatabase:
    def __init__(self):
        # 创建持久化向量数据库客户端
        self.client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(name="documents")
        # 加载嵌入模型
        print("正在加载嵌入模型...")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        print("嵌入模型加载完成！")

    def add_documents(self, documents: List[Tuple[str, Dict]]):
        """添加文档到向量数据库"""
        if not documents:
            print("警告：没有文档可添加")
            return
        texts = [doc[0] for doc in documents]
        metadatas = [doc[1] for doc in documents]
        ids = [f"{metadata['source']}_{metadata['chunk_id']}" for metadata in metadatas]
        print(f"正在处理 {len(texts)} 个文档块...")
        # 生成embedding
        print("正在生成嵌入向量...")
        embeddings = self.embedding_model.encode(texts).tolist()
        # 添加到集合
        print("正在添加到向量数据库...")
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        print(f"成功添加 {len(texts)} 个文档块到向量数据库")

    def search(self, query: str, n_results: int = 5) -> List[Tuple[str, Dict]]:
        """搜索相关文档"""
        if not query.strip():
            return []
        print(f"搜索查询: '{query}'")
        # 生成查询的embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        # 搜索
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        # 整理结果
        search_results = []
        if results['documents']:
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                search_results.append((doc, metadata))
        print(f"找到 {len(search_results)} 个相关文档块")
        return search_results

    def get_all_documents(self) -> List[str]:
        """获取所有文档名称"""
        try:
            results = self.collection.get()
            sources = set()
            for metadata in results['metadatas']:
                sources.add(metadata['source'])
            return list(sources)
        except Exception as e:
            print(f"获取文档列表时出错: {e}")
            return []

    def delete_document(self, source: str):
        """删除指定文档的所有块（支持原始文件名匹配）"""
        try:
            results = self.collection.get()
            ids_to_delete = []
            # 关键修改：解码传入的source（防止前端传递时编码残留）
            解码后的_source = urllib.parse.unquote(source)
            for i, metadata in enumerate(results['metadatas']):
                # 用解码后的文件名匹配元数据中的source
                if metadata['source'] == 解码后的_source:
                    ids_to_delete.append(results['ids'][i])
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                print(f"已删除文档 '{解码后的_source}' 的 {len(ids_to_delete)} 个块")
            else:
                print(f"未找到文档 '{解码后的_source}'")
        except Exception as e:
            print(f"删除文档时出错: {e}")


# 测试向量数据库
if __name__ == "__main__":
    # 创建测试数据（含中文文件名）
    test_documents = [
        ("人工智能是计算机科学的一个分支", {"source": "中文测试1.txt", "chunk_id": 0, "file_type": ".txt"}),
        ("深度学习是机器学习的一种方法", {"source": "中文测试1.txt", "chunk_id": 1, "file_type": ".txt"}),
        ("自然语言处理让计算机理解人类语言", {"source": "中文测试2.txt", "chunk_id": 0, "file_type": ".txt"})
    ]
    # 测试向量数据库
    print("=== 测试向量数据库 ===")
    db = VectorDatabase()
    # 添加文档
    print("\n1. 添加测试文档...")
    db.add_documents(test_documents)
    # 搜索测试
    print("\n2. 搜索测试...")
    results = db.search("什么是人工智能？")
    for i, (doc, metadata) in enumerate(results):
        print(f"结果 {i + 1}: {doc[:50]}... (来源: {metadata['source']})")
    # 获取文档列表
    print("\n3. 文档列表...")
    documents = db.get_all_documents()
    for doc in documents:
        print(f" - {doc}")
    # 删除测试
    print("\n4. 删除测试...")
    db.delete_document("中文测试1.txt")
    print("\n=== 向量数据库测试完成 ===")