import os
import PyPDF2
from docx import Document
from typing import List, Tuple
import re


class DocumentProcessor:
    def __init__(self, chunk_size=500, chunk_overlap=50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def read_pdf(self, file_path: str) -> str:
        """读取PDF文件"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"PDF读取错误: {e}")
        return text

    def read_docx(self, file_path: str) -> str:
        """读取Word文档"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
        except Exception as e:
            print(f"DOCX读取错误: {e}")
        return text

    def read_txt(self, file_path: str) -> str:
        """读取文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"TXT读取错误: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空格和换行
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()

    def split_text(self, text: str) -> List[str]:
        """将文本分割成块"""
        if len(text) <= self.chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            # 如果不在文本末尾，尝试在句子边界分割
            if end < len(text):
                # 找最近的句子结束符
                sentence_end = max(
                    text.rfind('。', start, end),
                    text.rfind('！', start, end),
                    text.rfind('？', start, end),
                    text.rfind('\n', start, end),
                    text.rfind('.', start, end)
                )
                if sentence_end != -1 and sentence_end > start:
                    end = sentence_end + 1
            chunk = text[start:end].strip()
            if chunk:  # 只添加非空块
                chunks.append(chunk)
            # 移动起始位置，考虑重叠
            start = end - self.chunk_overlap if end - self.chunk_overlap > start else end
            if start >= len(text):
                break
        return chunks

    # 关键修改：新增original_filename参数，接收原始文件名
    def process_document(self, file_path: str, original_filename: str = None) -> List[Tuple[str, dict]]:
        """处理文档并返回文本块（支持原始文件名传入）"""
        file_ext = os.path.splitext(file_path)[1].lower()
        print(f"处理文档: {file_path}, 类型: {file_ext}, 原始文件名: {original_filename}")

        # 读取文档
        if file_ext == '.pdf':
            text = self.read_pdf(file_path)
        elif file_ext == '.docx':
            text = self.read_docx(file_path)
        elif file_ext == '.txt':
            text = self.read_txt(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")

        if not text:
            raise ValueError("文档内容为空或读取失败")
        print(f"读取文本长度: {len(text)} 字符")

        # 清理文本
        text = self.clean_text(text)
        # 分割文本
        chunks = self.split_text(text)
        print(f"分割为 {len(chunks)} 个文本块")

        # 为每个块添加元数据（关键修改：使用原始文件名作为source）
        chunks_with_metadata = []
        for i, chunk in enumerate(chunks):
            metadata = {
                # 优先使用传入的原始文件名，否则用文件路径的basename
                "source": original_filename if original_filename else os.path.basename(file_path),
                "chunk_id": i,
                "file_type": file_ext
            }
            chunks_with_metadata.append((chunk, metadata))
        return chunks_with_metadata


# 测试文档处理
if __name__ == "__main__":
    processor = DocumentProcessor()
    # 创建一个测试文本文件（含中文文件名）
    test_text = """这是一个测试文档。
    用于验证文档处理功能是否正常工作。
    文档处理包括读取、清理和分割文本。
    分割后的文本块应该保持语义完整性。"""
    test_filename = "中文测试文档.txt"
    with open(test_filename, "w", encoding="utf-8") as f:
        f.write(test_text)
    # 测试处理（传入原始文件名）
    chunks = processor.process_document(test_filename, test_filename)
    for i, (chunk, metadata) in enumerate(chunks):
        print(f"块 {i}: {chunk[:50]}... (来源: {metadata['source']})")
    # 清理测试文件
    os.remove(test_filename)