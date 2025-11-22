import streamlit as st
import requests
import os
import urllib.parse

# 页面配置
st.set_page_config(
    page_title="文档智能问答系统",
    page_icon="📚",
    layout="wide",
    menu_items=None
)

# API基础URL
API_BASE = "http://localhost:8000"

# 初始化会话状态
if "聊天记录" not in st.session_state:
    st.session_state.聊天记录 = []
if "已上传文档" not in st.session_state:
    st.session_state.已上传文档 = []
if "文档ID到名称" not in st.session_state:
    st.session_state.文档ID到名称 = {}
if "名称到文档ID" not in st.session_state:
    st.session_state.名称到文档ID = {}
if "当前文件内容" not in st.session_state:
    st.session_state.当前文件内容 = None
if "当前文件名称" not in st.session_state:
    st.session_state.当前文件名称 = None
if "当前文件截断" not in st.session_state:
    st.session_state.当前文件截断 = False
if "当前模型" not in st.session_state:
    st.session_state.当前模型 = "deepseek"  # 默认模型


def 加载文档列表():
    """加载文档列表"""
    try:
        响应 = requests.get(f"{API_BASE}/documents")
        if 响应.status_code == 200:
            原始文档列表 = 响应.json()["documents"]
            st.session_state.已上传文档 = 原始文档列表
            return True
        else:
            st.session_state.已上传文档 = []
            return False
    except Exception as 错误:
        st.error(f"无法连接到后端服务: {错误}")
        st.session_state.已上传文档 = []
        return False


def 获取可用模型():
    """获取可用的AI模型列表"""
    try:
        响应 = requests.get(f"{API_BASE}/models")
        if 响应.status_code == 200:
            return 响应.json()["available_models"]
        else:
            return ["deepseek", "zhipu"]  # 默认列表
    except:
        return ["deepseek", "zhipu"]  # 默认列表


def 主函数():
    st.title("📚 文档智能问答系统")
    st.markdown("上传您的文档，然后与文档内容进行智能对话！")

    # 侧边栏 - 文档管理
    with st.sidebar:
        st.header("📁 文档管理")

        # AI模型选择
        st.subheader("🤖 AI模型选择")
        可用模型 = 获取可用模型()
        当前模型 = st.selectbox(
            "选择AI模型",
            可用模型,
            index=可用模型.index(st.session_state.当前模型) if st.session_state.当前模型 in 可用模型 else 0,
            key="模型选择"
        )
        if 当前模型 != st.session_state.当前模型:
            st.session_state.当前模型 = 当前模型
            st.rerun()

        st.divider()

        # 文件上传
        上传的文件 = st.file_uploader(
            "选择文档上传",
            type=['pdf', 'docx', 'txt'],
            help="支持PDF文档、Word文档、TXT文本文件，单个文件最大200MB"
        )

        if 上传的文件 is not None:
            if st.button("📤 上传文档", use_container_width=True):
                with st.spinner("正在处理文档..."):
                    try:
                        编码后的文件名 = urllib.parse.quote(上传的文件.name)
                        文件数据 = {"file": (编码后的文件名, 上传的文件.getvalue())}
                        响应 = requests.post(f"{API_BASE}/upload", files=文件数据)

                        if 响应.status_code == 200:
                            结果 = 响应.json()
                            st.success(f"✅ {结果['message']}")
                            st.info(f"文档被分割为 {结果['chunks_count']} 个文本块")

                            文档ID = 结果["document_id"]
                            原始文件名 = 上传的文件.name
                            st.session_state.文档ID到名称[文档ID] = 原始文件名
                            st.session_state.名称到文档ID[原始文件名] = 文档ID

                            加载文档列表()
                        else:
                            st.error(f"上传失败: {响应.json().get('detail', '未知错误')}")
                    except Exception as 错误:
                        st.error(f"上传失败: {str(错误)}")

        st.divider()

        # 文档列表
        st.subheader("已上传文档")
        加载文档列表()

        if st.session_state.已上传文档:
            for 原始文件名 in st.session_state.已上传文档:
                文档ID = st.session_state.名称到文档ID.get(原始文件名)
                列1, 列2 = st.columns([10, 1])
                with 列1:
                    if st.button(
                            原始文件名,
                            key=f"view_{原始文件名}",
                            use_container_width=True,
                            type="secondary"
                    ):
                        with st.spinner(f"正在加载 {原始文件名}..."):
                            try:
                                if 文档ID:
                                    编码后的文档ID = urllib.parse.quote(文档ID)
                                    响应 = requests.get(f"{API_BASE}/documents/{编码后的文档ID}/content")
                                    if 响应.status_code == 200:
                                        结果 = 响应.json()
                                        st.session_state.当前文件内容 = 结果["content"]
                                        st.session_state.当前文件名称 = 原始文件名
                                        st.session_state.当前文件截断 = 结果["truncated"]
                                    else:
                                        st.error(f"加载失败: {响应.json().get('detail', '未知错误')}")
                                else:
                                    st.error(f"未找到文档ID，请重新上传文档")
                            except Exception as 错误:
                                st.error(f"加载失败: {str(错误)}")
                with 列2:
                    if st.button("🗑️", key=f"删除_{原始文件名}"):
                        try:
                            if 文档ID:
                                编码后的文档ID = urllib.parse.quote(文档ID)
                                响应 = requests.delete(f"{API_BASE}/documents/{编码后的文档ID}")
                                if 响应.status_code == 200:
                                    st.success("文档已删除")
                                    if 原始文件名 in st.session_state.名称到文档ID:
                                        del st.session_state.名称到文档ID[原始文件名]
                                    if 文档ID in st.session_state.文档ID到名称:
                                        del st.session_state.文档ID到名称[文档ID]
                                    if st.session_state.当前文件名称 == 原始文件名:
                                        st.session_state.当前文件内容 = None
                                        st.session_state.当前文件名称 = None
                                    加载文档列表()
                                    st.rerun()
                                else:
                                    st.error("删除失败")
                            else:
                                st.error(f"未找到文档ID，无法删除")
                        except Exception as 错误:
                            st.error(f"删除失败: {str(错误)}")
        else:
            st.info("暂无上传文档")

        # 使用说明放在侧边栏底部
        st.divider()
        st.subheader("ℹ️ 使用说明")
        st.markdown(f"""
        ### 🚀 操作步骤：
        1. **选择模型** - 当前使用: **{st.session_state.当前模型.upper()}**
        2. **上传文档** - 上传PDF/Word/TXT文件
        3. **查看文档** - 点击文档名称查看内容
        4. **开始对话** - 在右侧输入问题

        ### 🤖 可用模型：
        - **DeepSeek**: 性价比高，响应快
        - **智谱AI**: 中文优化好，理解能力强

        ### ❓ 示例问题：
        - "总结文档的主要内容"
        - "文档中提到了哪些重要概念？"
        - "列出所有关键点"
        - "作者的主要观点是什么？"

        ### ⚠️ 注意事项：
        - 文档处理需要一些时间
        - 问题越具体，回答越准确
        - 支持PDF、DOCX、TXT格式
        """)

    # 主界面布局 - 右侧分为上下两部分
    右侧列 = st.container()

    with 右侧列:
        # 显示当前使用的模型
        st.info(f"当前使用AI模型: **{st.session_state.当前模型.upper()}**")

        # 上半部分：文件预览
        if st.session_state.当前文件名称 and st.session_state.当前文件内容:
            st.subheader(f"📄 {st.session_state.当前文件名称}")
            with st.expander("文件内容预览", expanded=True):
                st.text_area(
                    "内容:",
                    value=st.session_state.当前文件内容,
                    height=300,
                    disabled=True,
                    label_visibility="collapsed"
                )
                if st.session_state.当前文件截断:
                    st.info("⚠️ 注意：文件内容过长，已截断显示部分内容")
            st.divider()

        # 下半部分：问答区域
        st.subheader("💬 与文档对话")

        # 显示聊天历史
        for 对话 in st.session_state.聊天记录:
            with st.chat_message("user"):
                st.markdown(对话["问题"])
            with st.chat_message("assistant"):
                st.markdown(对话["回答"])
                if 对话["来源"]:
                    with st.expander("📄 参考来源"):
                        for 来源 in 对话["来源"]:
                            st.text(f"• {来源}")
                if 对话.get("模型"):
                    st.caption(f"使用模型: {对话['模型']}")

        # 聊天输入框
        问题 = st.chat_input("请输入您的问题...")

        if 问题:
            # 显示用户消息
            with st.chat_message("user"):
                st.markdown(问题)

            # 获取回答
            with st.chat_message("assistant"):
                with st.spinner(f"正在思考中，请稍候... (使用{st.session_state.当前模型.upper()})"):
                    try:
                        编码后的问题 = urllib.parse.quote(问题)
                        # 添加模型参数
                        url = f"{API_BASE}/chat?question={编码后的问题}&model={st.session_state.当前模型}"

                        响应 = requests.post(url)

                        if 响应.status_code == 200:
                            结果 = 响应.json()
                            st.markdown(结果["answer"])

                            # 显示来源
                            if 结果.get("sources"):
                                with st.expander(f"📄 参考来源 ({len(结果['sources'])}个文档)"):
                                    for 来源 in 结果["sources"]:
                                        st.text(f"• {来源}")

                            # 保存到聊天历史
                            st.session_state.聊天记录.append({
                                "问题": 问题,
                                "回答": 结果["answer"],
                                "来源": 结果.get("sources", []),
                                "模型": 结果.get("model_used", st.session_state.当前模型)
                            })
                        else:
                            st.error(f"获取回答失败 (状态码: {响应.status_code})")
                            try:
                                错误详情 = 响应.json()
                                st.write(f"错误详情: {错误详情}")
                            except:
                                st.write(f"响应内容: {响应.text}")
                    except Exception as 错误:
                        st.error(f"连接错误: {str(错误)}")


if __name__ == "__main__":
    主函数()