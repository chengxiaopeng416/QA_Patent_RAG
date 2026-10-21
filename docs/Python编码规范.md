# 华信科技 - Python 编码规范 V2.1

## 一、通用原则
- 遵循 PEP 8 风格指南。所有新项目使用 Python 3.11+。
- 最大行长度：120 个字符。所有源文件使用 UTF-8 编码。
- 所有公开函数和方法必须使用类型注解。

## 二、命名规范
- 模块：`lowercase_with_underscores.py`
- 类：`PascalCase`
- 函数/方法：`lowercase_with_underscores()`
- 常量：`UPPER_CASE_WITH_UNDERSCORES`
- 私有成员：使用单下划线前缀 `_private_method`

## 三、导入顺序
- 先导入标准库，再导入第三方库，最后导入本地模块。
- 优先使用绝对导入：`from utils.logger import setup_logger`
- 避免通配符导入：禁止使用 `from module import *`

## 四、类型注解
- 所有公开函数必须为参数和返回值添加类型注解。
- 可能为 None 的参数使用 `Optional[Type]`。
- 可能为多种类型的值使用 `Union[Type1, Type2]`。

## 五、错误处理
- 禁止使用裸 `except:`，必须指定捕获的异常类型。
- 所有异常应通过 `logger.error()` 记录到适当的日志级别。
- 针对业务特定的错误条件应抛出自定义异常。
- 不得静默忽略异常而不记录日志。

## 六、数据库操作
- 所有数据库交互使用 SQLAlchemy ORM。
- 始终使用参数化查询，禁止将用户输入拼接到 SQL 字符串中。
- 使用上下文管理器或 try/finally 块关闭数据库会话。
- 启用 `pool_pre_ping=True` 进行连接健康检查。

## 七、安全要求
- 所有密钥和凭证存储在 `.env` 文件中（禁止提交到版本控制）。
- 使用 `passlib` 配合 bcrypt 算法对密码进行哈希处理。
- 通过 Pydantic 模型验证对所有用户输入进行校验。
- JWT 令牌必须包含过期时间（访问令牌最长 48 小时）。
- 使用 `re.escape()` 转义来自用户输入的正则模式。

## 八、测试标准
- 所有项目使用 `pytest` 作为测试框架。
- 为所有工具函数和业务逻辑代理编写单元测试。
- 核心业务逻辑模块的目标代码覆盖率达到 80% 以上。
- 在测试套件中模拟外部依赖（LLM 服务、ChromaDB、Elasticsearch）。

## 九、文档要求
- 所有公开的模块、类和函数必须包含 Google 风格的文档字符串。
- 维护最新的 README.md，包含安装说明和 API 文档。
- 使用 FastAPI 自动 OpenAPI 文档（/docs）记录所有 API 端点。
- 在复杂函数和类的文档字符串中包含使用示例。
