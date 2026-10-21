# 技术专利/文献分析 Agent — 完整流程架构

> 基于 Agentic RAG 架构，专注技术专利/文献的智能检索、结构化提取与对比分析。
> 技术栈：FastAPI / Elasticsearch(BM25 + ik_max_word 分词) / Chroma 向量库(cosine) / Neo4j 三元组图谱 / CrossEncoder 重排 / Qwen 生成(OpenAI 兼容接口) / Ollama 本地向量模型 / Redis 缓存 / MySQL 用户管理。
> 运行：后端入口 `PARAG_main.py`（`fastapi dev` 启动）；前端为 Vite+Vue；中间件用 docker-compose 拉起 ES、Redis，本地运行 Neo4j、Ollama、Chroma。
> 说明：本文档为项目架构思路最终版，除标注「可扩展（未实现）」的章节外，其余流程均为已落地代码。

---


## 一、目标架构总览
### 1. 索引流程（上传文献时触发，离线执行）


```
POST /api/admin/upload（专利/PDF文献文件，JWT 认证）
        │
        ▼
 ① 查重：按文件名查 t_patent 表
     ├─ 已存在 → 直接返回"已存在该专利文档"，
     │           并顺便补全旧记录的 申请人/发明人/摘要/状态 等空字段
     └─ 未存在 → 继续走索引
        │
        ▼
 ② 解析 .md 元数据（申请人/发明人/摘要/状态/标题），落库 t_patent
        │
        ▼
  DocumentLoader 加载文档
   （pdf → MinerU；md → UnstructuredMarkdownLoader）
        │
        ▼
  DocumentSplitter 切分
   （RecursiveCharacterTextSplitter，512/50，
    separators = ["\n\n", "\n", "。", "？"]）
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
   Chroma 向量索引       ES BM25 索引       Neo4j 三元组索引
  （Ollama 本地向量， （ik_max_word 分词，  （LLM 提取三元组
   cosine 距离，        BM25 相似度）        {subject, predicate,
   按 200 条/批入库）                        object, constraint}，
                                            停用词过滤 + 同义词归一，
                                            :ENTITY 节点 + 中文关系 MERGE 入库）
```

### 2. 问答流程（在线执行，Agent 自主编排）

```
                 用户 Query
                     │
                     ▼
        [1] 策略分析工具 strategy_tool
            （LLM 分析 → retrieval_types + need_decomposition，
             结果按问题 MD5 缓存 Redis，默认 24h）
                     │
                     ▼
         ┌───────────┼───────────┐
         │           │           │
     简单问题      需拆分       复杂混合
     直接检索    TodoListMiddleware
         │        注入 write_todos
         │        拆解子任务列表
         │           │
         ▼           ▼
    [2] 按策略并行调用检索工具：
       ┌───────────┬───────────┬───────────┐
       ▼           ▼           ▼           ▼
 vector_retriever bm25_retriever hybrid_retriever graph_retriever
  （Chroma 语义） （ES 关键词） （向量+BM25  （Neo4j 实体
    score≤0.7）                 +RRF 融合，  路径提取）
                                score≤0.5）
       │           │           │           │
       │           │           │           │  ← graph 特殊处理：
       │           │           │           │     ①LLM 抽取实体
       │           │           │           │     ②:ENTITY 双向检索
       │           │           │           │     ③关系类型过滤+去重
       └───────────┴───────────┴───────────┘
                     │
                     ▼
         [3] 各工具把文档经 MD5 映射成 doc_id 存入
             DocStore，返回 doc_id + snippet（前100字）
                     │
                     ▼
         [4] Agent 合并去重 doc_id 列表
                     │
                     ▼
         [5] 调用 rerank_doc 工具
             （CrossEncoder 精排（top_n=10），
              从 DocStore 取回全文，超过 50 篇先截断）
                     │
                     ▼
         [6] Agent 基于精排后的文档生成最终回答，
             通过 SSE 事件流逐段下发：
             strategy → todos → tool_start/tool_end（多路可并行）
             → answer（5字/块打字机） → done（含引用文档）
             （回答含技术对比表格、引用标注）
```

---

### 3. 步骤与代码对照（答辩索引）
AI写的：
service/doc_service.py	全篇「比喻：…」风格（文件柜/登记表）
api_router/doc_api_router.py	全篇「比喻：前端说…」
主要帮我解决了前端的查看摘要和删除专利

api_router/file_upload_api_router.py	头部「【我新加的功能】」+ 查重/补全逻辑
要获取那些特殊的摘要信息，就要专门去分割

service/chat_service.py	「【我重写的方法】」「关键修复点」
原版的逻辑是"看到任意一个工具结果(ToolMessage)后，后续所有AI文本
都当成最终答案推送"，导致工具调用间隙的过渡语（"接下来我将..."）
全被推到前端，用户看到分析结果里全是思考过程。
现在的逻辑：只有 agent 不再调用任何工具时输出的 AIMessage 才是真答案。

PA_RAG_retriever/rrf_fusioner_retriever.py	全篇分步讲解 +「举例：…计算…」算例
实现的功能上与前者一样 但它是继承父类EnsembleRetriever仅补写rrf_score的黑盒写法：去重键、排序、融合过程都在框架里，
我没法按自己的链路调。我重写为独立的 RRFFusioner，每一行都自己掌控，这样多路融合公式、去重、排序、分数都可控

database/clean_chroma.py	全篇【】标记 + PyCharm 一键运行提示，一看就是独立新工具

> 下表把问答流程每一步都指向源码位置（`文件:行号` 会随后续改动微移，但模块与函数名稳定）。

| 步骤                 | 做了什么                                                                                                                                | 代码位置                                                                                                                 |
|--------------------|-------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| ① 接口入口             | `GET /api/chat/ask`（SSE）                                                                                                            | `api_router/chat_api_router.py:19`                                                                                   |
| ① 策略分析             | `strategy_tool` 工具定义                                                                                                                | `tools/strategy_tool.py:23`（@tool 在 :22）                                                                             |
| ① 策略规则             | `ANALYZE_PROMPT`（四种检索方式 + 判断规则 + JSON Schema）                                                                                       | `PARAG_agent/prompt.py:8`                                                                                            |
| ① 结构化输出            | `qwen_llm.with_structured_output(StrategyAnalyzer)`（Pydantic 强约束返回 `retrieval_types/need_decomposition/sub_queries_hint/reasoning`） | `tools/strategy_tool.py:47`                                                                                          |
| ① Redis 缓存         | 先查缓存（MD5 命中直接返回）→ 未命中调 LLM → 写缓存                                                                                                    | `tools/strategy_tool.py:37,40,56`；实现 `service/redis_service.py:54,66`；TTL 默认 86400s `utils/config.py:51`             |
| 拆分子任务              | `TodoListMiddleware` 注入 `write_todos` 工具                                                                                            | `PARAG_agent/chat_agent.py:5,30`                                                                                     |
| ② Agent 编排         | `create_agent` 组装 6 个工具 + 中间件 + 系统提示词                                                                                               | `PARAG_agent/chat_agent.py:15-31`                                                                                    |
| ② 工具集              | 四路检索 + 重排工具创建                                                                                                                       | `tools/rrf_retriever_tool.py:21`（`create_retriever_tools`）                                                           |
| ② vector_retriever | 语义检索（Chroma，score≤0.7）                                                                                                              | `tools/rrf_retriever_tool.py:46`；实现 `PA_RAG_retriever/vector_retriever.py:43`；向量库 `models/chroma.py:9-19`            |
| ② bm25_retriever   | 关键词检索（ES + ik 分词）                                                                                                                   | `tools/rrf_retriever_tool.py:77`；实现 `PA_RAG_retriever/ES_bm25_retriever.py`                                          |
| ② hybrid_retriever | 向量 + BM25 双路召回，RRF 融合（权重 0.5/0.5，c=60，score≤0.5）                                                                                    | `tools/rrf_retriever_tool.py:105-145`；融合器 `PA_RAG_retriever/rrf_fusioner_retriever.py`                               |
| ② graph_retriever  | 实体抽取→`:ENTITY` 双向匹配→关系类型过滤→去重→路径文本                                                                                                  | `tools/rrf_retriever_tool.py:149`；实现 `PA_RAG_retriever/neo4j_retriever.py:112`（extract :28 / retrieve :45 / 去重 :99）  |
| ③ DocStore         | doc_id = 内容 MD5 前16位，正文收进服务端字典，只回传 doc_id + snippet                                                                                 | `tools/doc_store.py:20,24,46`；snippet 100 字上限 `utils/config.py:57`；打包逻辑 `tools/rrf_retriever_tool.py:29`（to_compact） |
| ④ 合并去重             | 由 Agent 自主合并 doc_id，提示词约束"必须先合并去重再传入 rerank_doc"                                                                                    | `PARAG_agent/prompt.py:73`                                                                                           |
| ⑤ rerank_doc       | 从 DocStore 取回全文→超 50 篇截断→CrossEncoder 精排（top_n=10）                                                                                  | `tools/reranker_tool.py:18-42`；模型单例 `reranker/reranker.py:16,24,46`；上限 `utils/config.py:53`                          |
| ⑥ 流式生成             | `generator` 消费 `agent.astream(stream_mode=["updates","messages"])`，拼装 SSE 事件                                                        | `service/chat_service.py:79`（astream :96；事件构造 `sse_event` :21）                                                       |
| ⑥ 事件类型             | `strategy` :146 / `todos` :124 / `tool_start` :137 / `tool_end` :150 / `answer` :170 / `done` :173                                  | `service/chat_service.py`                                                                                            |
| ⑥ 换行保真             | `answer_pieces` 按整行切块 + JSON 编码，防 SSE 帧被 `\n` 拆断                                                                                    | `service/chat_service.py:28`                                                                                         |
| ⑥ 前端渲染             | 事件分流 `handleFrame`、markdown 渲染 + 标题/列表预处理、表格样式                                                                                      | `parag-front/src/views/ChatView.vue:180`；`parag-front/src/utils/markdown.js:15`                                      |
| 备用                 | 非流式接口 `POST /api/chat/invoke`（一次返回 answer + todos + references）                                                                     | `api_router/chat_api_router.py:34`；`service/chat_service.py:31`                                                      |

> 说明：[1] 策略分析 → [6] 最终回答的具体行为由系统提示词 `AGENT_SYSTEM_PROMPT` 驱动
> （`PARAG_agent/prompt.py:57`）；LLM 实例在 `models/my_llm.py:10`（Qwen，`max_tokens=4096`）。

**核心原则：策略分析管"走哪条路"，TodoList 管"怎么拆任务"，DocStore 管"文档怎么传"，Rerank 管"结果怎么排"。**

---

## 二、Neo4j 三元组图谱（实际实现 Schema）

> 实际落地未按专利/技术/问题等预定义节点类型，而是采用**通用实体节点的开放式三元组**：入库灵活、无需预先建模，实体名（name 属性）即节点的唯一身份。

### 节点类型（统一通用标签）

```
:ENTITY   （所有实体共用 ENTITY 标签，身份由 name 属性唯一标识）
          实体来源：技术方案、材料、方法、专利名称、发明人、申请人、
          技术领域、技术问题、技术效果、产品、参数 等
```

### 关系类型（三元组的 predicate 直接作为关系 label）

```
(s:ENTITY {name:'...'}) -[:采用]->     (o:ENTITY)     （使用/利用 → 采用）
(s:ENTITY)              -[:解决]->     (o:ENTITY)     （克服/改善 → 解决）
(s:ENTITY)              -[:提出]->     (o:ENTITY)     （公开/揭示 → 提出）
(s:ENTITY)              -[:属于]->     (o:ENTITY)     （归类于/分类为 → 属于）
(s:ENTITY)              -[:包含]->     (o:ENTITY)     （包括/含有 → 包含）
(s:ENTITY)              -[:基于]->     (o:ENTITY)     （根据/依据 → 基于）
(s:ENTITY)              -[:涉及]->     (o:ENTITY)     （关于/关联 → 涉及）
(s:ENTITY)              -[:应用于]->   (o:ENTITY)     （适用于/用于 → 应用于）
(s:ENTITY)              -[:改进]->     (o:ENTITY)     （优化/提升/增强 → 改进）
（关系可带 constraint 属性，保存温度/压力/比例等工艺条件）
```

### 三元组加工流水线（neo4j_index.py）

1. **提取**：LLM 读整篇文档，输出 JSON 数组 `[{"subject","predicate","object","constraint"}]`，一个技术方案至少 1~5 条三元组。
2. **清洗**（clean_triples）：
   - 去掉缺主体/谓语/客体的不完整三元组、单字实体；
   - **停用词过滤**（的/了/是/一种/本发明/方法/装置/系统…）；
   - **同义词归一**（本发明→该技术方案、权利要求→技术方案、有益效果→技术效果、对比文件→现有技术…）；
   - **关系归一**（使用/利用→采用、克服/改善→解决、公开/揭示→提出、优化/提升/增强→改进…）；
   - 按 `(subject, predicate, object, constraint)` 去重。
3. **入库**：`MERGE (s:ENTITY{name}) -[r:关系]-> (o:ENTITY{name})`，`SET r.constraint = ...`；delete_flag=True 时先清空全图。

### 示例 Cypher（实际写入）

```cypher
// 创建实体节点 + 带条件的采用关系
MERGE (s:ENTITY {name: '相变材料热管理方法'})
MERGE (o:ENTITY {name: '相变材料'})
MERGE (s)-[:采用]->(o) SET r.constraint = '相变温度 28~45℃'
```

---

## 三、策略分析规则（LLM 识别意图）

> 规则实现在 `PARAG_agent/prompt.py` 的 `ANALYZE_PROMPT`：`strategy_tool` 调用 Qwen，以 Pydantic 结构化输出
> `{retrieval_types, need_decomposition, sub_queries_hint, reasoning}`，结果按问题 MD5 缓存 Redis（默认 24h，失败自动降级为无缓存）。

| 用户问题类型 | 策略分析结果 | 检索方式 |
|---|---|---|
| "这个专利的创新点是什么？" | 单专利查询 | vector + graph |
| "XX领域有哪些技术方案？" | 领域检索 | vector + bm25 + graph |
| "A专利和B专利的区别？" | 对比分析（需拆分） | TodoList → 分别检索 → 对比 |
| "CN20241001的技术方案" | 精确专利号 | bm25 + graph |
| "热管理领域的专利规避方案" | 混合检索 | 全部检索 + rerank |
| "帮我总结这个领域的技术趋势" | 复杂综合（需拆分） | TodoList → 多维度检索 → 综合 |

---

## 四、Neo4j 图检索工具（实际实现）

> 检索器 `PA_RAG_retriever/neo4j_retriever.py` 不直接生成 Cypher 匹配专利号/领域，而是走**实体抽取 + 双向路径检索**：
> 图检索只关注"实体间的关系路径"（谁采用/解决了谁），纯语义联想部分由 vector/hybrid 兜底。

```
用户问题
    │
    ▼
① LLM 抽取关键实体（技术方案/方法/材料/技术领域/技术问题…）
   返回实体名列表，如 ["电池热管理", "相变材料"]
    │
    ▼
② 对每个实体做双向路径检索（带关系类型过滤）
   MATCH (s:ENTITY {name:$实体}) -[r]-> (o:ENTITY)
   WHERE type(r) IN ['采用','解决','应用于','提出','改进']
   UNION
   MATCH (s:ENTITY) <-[r]- (o:ENTITY {name:$实体})
   WHERE type(r) IN ['采用','解决','应用于','提出','改进']
    │
    ▼
③ 按 (subject, predicate, object, constraint) 去重
    │
    ▼
④ 封装为路径文本，作为检索工具输出
   "实体A → 采用 → 实体B (条件: 相变温度 28~45℃)"
   （打包进 DocStore，doc_id 参与后续统一 rerank）
```

> 说明：当问题里没有明确实体（纯语义、开放式提问）时，LLM 抽取到的实体少、图检索召回有限，
> 由策略分析选中的 vector / hybrid 检索兜底，保证结果覆盖面。

---

## 五、Agent 输出格式（专利分析专用）

> 生成要求实现在 `PARAG_agent/prompt.py` 的 `AGENT_SYSTEM_PROMPT`：回答必须基于检索到的文献、引用具体专利号；
> 涉及技术对比用结构化表格，涉及技术演进用时间线/因果链；检索结果不足时明确告知用户。

```markdown
## 技术对比分析

### CN20241001 — 相变材料热管理方案
| 维度 | 内容 |
|------|------|
| 技术方案 | 采用石蜡基相变材料包裹电池模组 |
| 创新点 | 相变材料微胶囊化，导热系数提升40% |
| 应用场景 | 新能源汽车动力电池热管理 |
| 优势 | 被动散热，无需额外能耗 |
| 来源 | 【专利原文1】 |

### CN20231088 — 液冷循环热管理方案
| 维度 | 内容 |
|------|------|
| 技术方案 | 微通道液冷板+乙二醇冷却液循环 |
| 创新点 | 流道拓扑优化，压降降低35% |
| 应用场景 | 高功率密度电芯散热 |
| 优势 | 主动散热效率高，温度均匀性好 |
| 来源 | 【专利原文2】 |

### 核心差异
两者采用不同技术路线：被动散热 vs 主动散热，
适用场景不同...【依据来自原文片段】
```

---

## 六、与企业问答融合接口（跨项目对接设想，未接入）

> 本项目当前是独立 FastAPI 应用（`PARAG_main.py`），不依赖其他项目的 agent_graph。若要与"企业问答 Agent"融合，可在其 agent_graph 中新增分支：

```
classify → agent_qa | recommend | patent_analysis（新增）
```

`patent_analysis` 节点接入本项目 Agent，检索工具复用现有 Chroma/ES/Neo4j；
企业问答用通用三元组图谱，本项目用开放式 `:ENTITY` 三元组图谱，两者物理隔离、互不污染。

---

## 七、与 Agentic RAG（项目2）的架构差异

| 维度 | Agentic RAG（企业问答） | 技术专利分析 Agent |
|---|---|---|
| 文档类型 | 企业内部知识文档 | 专利文献/技术报告 |
| 三元组 schema | 通用 subject-predicate-object | 开放式三元组（:ENTITY 通用节点 + 中文关系标签） |
| 图检索方式 | 通用实体双向匹配 | 实体名双向路径检索 + 关系类型过滤/去重 |
| 输出格式 | 文本回答 | 结构化对比表格 + 引用标注 |
| 策略分析 | 问答类型分类 | 专利查询/领域检索/对比分析/趋势总结 |
| 复杂任务 | 一般拆解 | 专利对比需拆分为多路独立检索 |

---

## 八、可扩展方向（以下均为未实现，作为答辩展望）

> 当前版本只实现了"检索增强/生成增强/Agentic 进阶"中的基础能力：多路检索、RRF 融合、重排、SSE、策略缓存、TodoList 拆解均已落地；以下条目为后续可扩展点。

### 8.1 检索增强

| 方向 | 做法 | 解决什么问题 |
|---|---|---|
| 专利分类号过滤 | IPC/CPC 分类号作为元数据前置过滤 | 缩小检索范围，提高精准度 |
| 时间线检索 | 按申请/公开时间排序筛选 | "最近3年该领域的专利趋势" |
| 引用网络 | 构建专利间引用关系图谱 | 追溯技术演进脉络 |

### 8.2 生成增强

- **引用溯源**：答案关键句标注来源专利号 + 原文片段
- **技术路线图**：基于图谱关系生成技术演进时间线
- **专利地图**：按技术领域聚合生成热力分布概览

### 8.3 Agentic 进阶

- 注册 `search_patent` / `search_technology` / `get_document` 为工具，Agent 自主规划调用
- 复杂问题时启动 Agent 循环，普通问题走固定管道
