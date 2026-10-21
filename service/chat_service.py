"""
Agent RAG 聊天服务。

与classic版本差异：
- 不再是"固定检索管线+LLM回答"，而是由Agent自主编排：策略分析→(拆解)→多路并行
  检索→合并→统一rerank→生成回答
- SSE输出为结构化事件流：strategy / todos / tool_start / tool_end / answer / done
- 每个请求创建独立的DocStore与Agent实例（方案A：doc_id+服务端Store）
"""
import json

from langchain_core.messages import AIMessage, ToolMessage

from PARAG_agent.chat_agent import build_chat_agent
from tools.doc_store import DocStore
from utils.logger import setup_logger

logger = setup_logger(__name__)


def sse_event(event: str, data) -> str:
    """构造SSE格式事件帧"""
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


def answer_pieces(text: str, max_line: int = 80):
    """
    把最终答案按"整行"切块，用于流式发送。

    为什么必须这样做：
    1. SSE 协议里 data: 一行内不允许出现裸换行，前端解析只认 data: 前缀行，
       凡是被 \n 拆到第二行的内容全会被丢弃 —— 以前按固定5字符切块，
       只要块里碰巧带换行符，答案所有的换行就都丢了，最终整段挤成一行。
    2. 这里按 \n 分块，每一块都是完整的一行（行超长再折半），
       让前端 marked 能解析出标题/列表/表格，同时保留打字机流式效果。
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        while len(line) > max_line:
            yield line[:max_line]
            line = line[max_line:]
        if i < len(lines) - 1:
            line += "\n"
        if line:
            yield line


class AgentChatService:

    # ==================== 非流式调用 ====================
    async def invoke(self, query: str) -> dict:
        doc_store = DocStore()
        agent = build_chat_agent(doc_store)

        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": query}]
        })

        todos = result.get("todos", [])
        answer = result["messages"][-1].content
        references = self._collect_references(doc_store)

        logger.info(f"Agent执行完成: todos={len(todos)}, 引用文档={len(references)}")

        return {
            "answer": answer,
            "todos": todos,
            "references": references
        }

    # ==================== SSE流式调用 ====================
    # 【我重写的方法】：
    # 原版的逻辑是"看到任意一个工具结果(ToolMessage)后，后续所有AI文本
    #  都当成最终答案推送"，导致工具调用间隙的过渡语（"接下来我将..."）
    #  全被推到前端，用户看到分析结果里全是思考过程。
    # 现在的逻辑：只有 agent 不再调用任何工具时输出的 AIMessage 才是真答案。
    async def generator(self, query: str):
        """SSE事件流：
        strategy → todos → tool_start/tool_end（可并行多路） → answer(token流) → done
        """
        doc_store = DocStore()
        agent = build_chat_agent(doc_store)

        try:
            # 是否已输出过最终答案（避免后续重复推送）
            answer_sent = False
            # 候选最终答案：只在"agent 不再调用任何工具"的那一轮收集，
            # 一旦之后又出现工具调用，说明之前那句只是过渡语，作废。
            pending_answer = None
            latest_todos = []

            async for mode, chunk in agent.astream(
                    {"messages": [{"role": "user", "content": query}]},
                    stream_mode=["updates", "messages"]
            ):
                if mode == "messages":
                    msg = chunk[0] if isinstance(chunk, tuple) else chunk

                    # 关键修复点：
                    # 之前的做法是"看到任意一个工具结果(ToolMessage)后，
                    #  后续所有AI文本都当成最终答案推送"
                    # 这会导致AI在工具调用间隙说的过渡语（如"接下来我将..."）
                    #  被误当成答案，用户看到的全是思考过程。
                    # 现在改为：只有 agent 不再调用任何工具时输出的
                    #  AI 文本（没有 tool_calls 的 AIMessage）才是真正答案，
                    #  这里只负责收集，真正的答案在 updates 分支里推送。
                    pass

                elif mode == "updates":
                    # 本轮 agent 有没有调用工具？如果有，说明这轮输出的是过渡语
                    has_tool_call = False
                    candidate_answer = None

                    for node_update in chunk.values():
                        if not isinstance(node_update, dict):
                            continue

                        # todo进度更新
                        todos = node_update.get("todos")
                        if todos:
                            latest_todos = todos
                            yield sse_event("todos", [
                                {"content": t.get("content"), "status": t.get("status")}
                                for t in todos
                            ])

                        messages = node_update.get("messages", [])
                        for msg in messages:
                            # AI消息带tool_calls → 工具开始执行（这轮是过渡语）
                            tool_calls = getattr(msg, "tool_calls", None)
                            if tool_calls:
                                has_tool_call = True
                                pending_answer = None  # 之前若缓存过过渡语，作废
                                for tc in tool_calls:
                                    yield sse_event("tool_start", {
                                        "name": tc.get("name"),
                                        "args": tc.get("args", {})
                                    })

                            # 策略分析结果单独推送
                            if isinstance(msg, ToolMessage) and msg.name == "strategy_tool":
                                strategy = self._parse_strategy(msg.content)
                                if strategy is not None:
                                    yield sse_event("strategy", strategy)

                            # 工具结果返回，ToolMessage产生表示工具已经执行完成
                            if isinstance(msg, ToolMessage):
                                yield sse_event("tool_end", {"name": msg.name})

                            # 候选最终答案：AIMessage 且不带 tool_calls
                            if isinstance(msg, AIMessage) and not tool_calls:
                                content = msg.content if isinstance(msg.content, str) else ""
                                if content:
                                    candidate_answer = content

                    # 本轮没有调用工具却有纯文本AI输出 → 记入候选最终答案
                    if not has_tool_call and candidate_answer:
                        pending_answer = candidate_answer

            # 循环结束：pending_answer 即 agent 最后一次"不再调用工具"的文本输出（最终答案）。
            # 之前版本是"某个无工具调用的轮次一出现就立刻发答案 + answer_sent 置 True"，
            # 一旦模型先说了过渡语（"我将调用 rerank_doc…"）再真正回答，真正答案就被挡掉，
            # 用户看到的结果就只有一句过渡语和一段残片。延迟到最后发能保证内容完整。
            if pending_answer and not answer_sent:
                answer_sent = True
                # 按整行切块 + JSON编码发送：保留 \n（若裸发，换行会被SSE帧拆丢）
                for piece in answer_pieces(pending_answer):
                    yield sse_event("answer", json.dumps(piece, ensure_ascii=False))

            # 结束事件：附带todos最终状态与引用文档
            yield sse_event("done", {
                "todos": [
                    {"content": t.get("content"), "status": t.get("status")}
                    for t in latest_todos
                ],
                "references": self._collect_references(doc_store)
            })
        except Exception as e:
            logger.error(f"Agent执行异常: {e}")
            yield sse_event("error", {"message": f"服务执行异常: {str(e)[:200]}"})
            yield sse_event("done", {"todos": [], "references": []})

    # 解析策略分析工具的返回内容
    @staticmethod
    def _parse_strategy(content) -> dict | None:
        try:
            raw = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            return json.loads(raw)
        except Exception as e:
            logger.error(f"策略分析结果解析失败: {e}")

    # 收集本请求DocStore中的引用文档（doc_id + 摘要）
    @staticmethod
    def _collect_references(doc_store: DocStore) -> list[dict]:
        references = []
        for doc_id, doc in doc_store.items():
            references.append({
                "doc_id": doc_id,
                "snippet": doc_store.get_snippet(doc),
                "source": doc.metadata.get("source", "")
            })
        return references


