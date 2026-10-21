# 企业知识问答系统V3.0 - 技术架构设计

**作者：李娜 | 日期：2026-06-15 | 内部文档**

## 一、技术栈

- **后端**：Python 3.11 + FastAPI + LangGraph/LangChain
- **前端**：原生JavaScript单页应用
- **数据库**：MySQL 8.0 + ChromaDB + ES 8.x
- **大语言模型**：Qwen3-8B (Ollama) / 嵌入模型：nomic-embed-text
- **基础设施**：Kubernetes + Docker + Nginx

## 二、架构分层

| 层级 | 说明 |
|------|------|
| **表现层** | 端口8082的SPA应用，SSE流式传输，API代理到8000端口 |
| **API层** | FastAPI路由：/auth /chat /knowledge /recommend /feedback /admin |
| **编排层** | LangGraph主图：意图分类→5个代理。RAG子图：数据库查询+知识库检索+重排序+生成 |
| **检索层** | 混合搜索：ChromaDB向量搜索+ES BM25全文搜索，RRF融合，基于嵌入的重排序 |
| **数据层** | MySQL（元数据/用户/历史记录），ChromaDB（向量），ES（全文搜索） |

## 三、数据流程

1. 用户通过SPA提交问题→代理转发到FastAPI
2. JWT认证，从MySQL加载聊天历史
3. 主图分类意图（问答/推荐/创建/反馈/管理）
4. 问答→RAG子图：意图分类（数据库查询 vs 知识库）→混合搜索→重排序→生成回答
5. 通过SSE流式传输回答，保存到MySQL
