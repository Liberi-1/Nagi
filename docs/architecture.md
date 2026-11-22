# Nagi 架构

&gt; 当前版本：v0.2  
&gt; 核心原则：保持 v0.1 实时语音链路和 Unity 请求方式可用，在不重写客户端的前提下加入 MySQL、Redis、多轮上下文和 Web 管理后台。

## 设计原则

1. **MySQL 是权威数据源**：用户、启用人设和完整对话记录最终以 MySQL 为准。
2. **Redis 只是上下文缓存**：Redis 不保存 MySQL 中没有的权威数据，缓存失效不能阻断语音主流程。
3. **实时对话与管理接口分离**：WebSocket 负责 Unity 语音对话，FastAPI 负责 Vue 管理后台。
4. **按会话隔离上下文**：同一 WebSocket 连接共享一个 `session_id`，不同会话不会混用历史。
5. **有限上下文**：默认只把最近 10 轮发送给 LLM，完整历史仍保留在 MySQL。
6. **本地单用户优先**：v0.2 不提前引入登录、权限、微服务或向量长期记忆。

## 整体架构

```mermaid
flowchart LR
    subgraph Client["Unity 客户端"]
        MIC["麦克风录音"]
        PLAYER["回复语音播放"]
        AVATAR["Idle / Talking 动画"]
    end

    subgraph Realtime["实时对话后端"]
        WS["server.py&lt;br/&gt;WebSocket :8765"]
        PIPE["pipeline.py&lt;br/&gt;对话管线"]
    end

    subgraph AI["AI 与媒体服务"]
        ASR["Whisper ASR"]
        LLM["DeepSeek LLM"]
        TTS["Edge TTS"]
    end

    subgraph Data["数据层"]
        REDIS[("Redis&lt;br/&gt;最近 N 轮上下文")]
        MYSQL[("MySQL&lt;br/&gt;用户 / 人设 / 完整对话")]
    end

    subgraph Management["管理服务"]
        ADMIN["Vue 管理后台 :5173"]
        API["api.py&lt;br/&gt;FastAPI :8000"]
    end

    MIC --&gt;|"chat_request&lt;br/&gt;JSON 头 + WAV"| WS
    WS --&gt; PIPE
    PIPE --&gt; ASR
    ASR --&gt;|"用户文本"| PIPE
    PIPE --&gt;|"人设 + 历史 + 当前输入"| LLM
    LLM --&gt;|"回复文本"| PIPE
    PIPE --&gt;|"回复文本"| TTS
    TTS --&gt;|"MP3 文件"| PIPE
    PIPE --&gt; WS
    WS --&gt;|"chat_response&lt;br/&gt;JSON 头 + MP3"| PLAYER
    WS --&gt;|"emotion"| AVATAR

    PIPE &lt;--&gt;|"读取 / 重建 / 追加缓存"| REDIS
    PIPE &lt;--&gt;|"读取人设与历史&lt;br/&gt;保存完整对话"| MYSQL

    ADMIN &lt;--&gt;|"HTTP /api"| API
    API &lt;--&gt;|"人设 / 日志 / 统计"| MYSQL
    API --&gt;|"音色试听文本"| TTS
    TTS --&gt;|"临时 MP3"| API
    API --&gt;|"audio/mpeg"| ADMIN
```

Unity 不直接读取数据库人设，也不直接访问 FastAPI。人设由 Pipeline 在每轮对话时从 MySQL 加载。

## 进程与入口

| 组件 | 入口 | 默认地址 | 职责 |
| --- | --- | --- | --- |
| WebSocket 服务 | `backend/server.py` | `ws://localhost:8765` | Unity 连接、音频收发、会话创建、请求配对 |
| 对话管线 | `backend/pipeline.py` | 由 WebSocket 调用 | ASR、上下文、LLM、入库、缓存和 TTS 编排 |
| 管理接口 | `backend/api.py` | `http://127.0.0.1:8000` | 人设、日志、统计、健康检查和 TTS 试听 |
| 管理后台 | `web-admin/` | `http://localhost:5173` | Vue 开发服务器和管理界面 |
| MySQL | 外部本地服务 | `localhost:3306` | 权威持久化数据 |
| Redis 兼容服务 | Memurai Developer | `127.0.0.1:6379` | 最近对话上下文缓存 |

FastAPI 与 WebSocket 是两个独立进程。停止 FastAPI 会中断管理后台，但不会改变已有 WebSocket 会话的 `session_id`；重启 WebSocket 服务则会断开当前实时连接。

## 实时对话时序

```mermaid
sequenceDiagram
    autonumber
    participant U as Unity
    participant W as WebSocket
    participant P as Pipeline
    participant A as Whisper
    participant R as Redis
    participant M as MySQL
    participant L as DeepSeek
    participant T as Edge TTS

    U-&gt;&gt;W: 建立 WebSocket 连接
    W-&gt;&gt;W: 为连接生成 session_id

    U-&gt;&gt;W: chat_request + WAV
    W-&gt;&gt;P: process(session_id, request_id, context_turns)
    P-&gt;&gt;A: 识别音频
    A--&gt;&gt;P: 用户文本

    P-&gt;&gt;M: 读取默认用户和当前启用人设
    M--&gt;&gt;P: user_id + persona

    P-&gt;&gt;R: 读取当前 session_id 的最近 N 轮

    alt Redis 命中
        R--&gt;&gt;P: 历史 user / assistant 消息
    else 未命中、损坏、被跳过或不可用
        P-&gt;&gt;M: 查询同一会话最近 N 轮
        M--&gt;&gt;P: MySQL 历史记录
        P-&gt;&gt;R: replace_cache 重建缓存
    end

    P-&gt;&gt;L: system 人设 + 历史消息 + 当前用户输入
    L--&gt;&gt;P: 角色回复文本

    P-&gt;&gt;M: 保存本轮用户输入和角色回复
    M--&gt;&gt;P: 保存成功

    P-&gt;&gt;R: RPUSH 本轮 + LTRIM 最近 N 轮 + EXPIRE
    P-&gt;&gt;T: 合成回复文本
    T--&gt;&gt;P: 独立 MP3 文件

    P--&gt;&gt;W: 文本、音频、emotion、session_id、request_id
    W--&gt;&gt;U: chat_response + MP3
    U-&gt;&gt;U: 播放语音并切换 Talking 动画
```

对话在 **LLM 成功后、TTS 前**写入 MySQL。因此 Edge TTS 网络失败时，本轮文字对话仍然保留。

MySQL 保存成功后必须执行 Redis 追加。追加逻辑独立于数据库异常处理块，不能放在 `except` 或 `raise` 之后。

## LLM 消息结构

每轮发送给 DeepSeek 的消息按以下顺序构造：

```text
system：MySQL 中当前启用的人设
user：历史第 1 轮用户输入
assistant：历史第 1 轮角色回复
……
user：历史第 N 轮用户输入
assistant：历史第 N 轮角色回复
user：本轮用户输入
```

约束：

- 历史记录只允许展开为 `user` 和 `assistant`。
- 历史对话不能注入额外的 `system` 消息。
- 当前用户输入始终位于消息列表末尾。
- 构造消息时不修改调用方传入的历史列表。
- 默认 `context_turns=10`，即最多 10 轮、20 条历史消息。
- `context_turns=0` 时禁用历史上下文，但仍可保存完整对话。

## MySQL 数据模型

### `users`

保存本地用户：

- `id`
- `username`
- `display_name`
- `created_at`

v0.2 默认使用 `local` 用户，不提供多用户登录。

### `personas`

保存用户人设：

- `id`
- `user_id`
- `name`
- `content`
- `is_active`
- `created_at`
- `updated_at`

Pipeline 每轮读取当前启用人设。`backend/config/persona.md` 仅用于首次初始化，不会在运行时覆盖数据库人设。

### `conversation_records`

一行保存一轮完整对话：

- `id`
- `user_id`
- `persona_id`
- `session_id`
- `request_id`
- `user_text`
- `assistant_text`
- `emotion`
- `created_at`

其中：

- `session_id` 用于隔离不同实时会话；
- `request_id` 用于配对客户端请求和响应；
- `request_id` 不用于查询多轮上下文；
- 最近历史先按 ID 倒序取 N 条，再反转为时间正序；
- 日志页面按 ID 倒序展示，最新记录排在前面；
- 当前 `emotion` 仍固定为 `neutral`。

## Redis 缓存结构

缓存键：

```text
nagi:context:{user_id}:{session_id}
```

每个 List 项是一轮 JSON：

```json
{
  "user_text": "用户输入",
  "assistant_text": "角色回复"
}
```

List 按时间正序保存：

- `RPUSH`：在末尾追加新一轮；
- `LRANGE key -N -1`：读取最近 N 轮；
- `LTRIM key -N -1`：只保留最近 N 轮；
- `EXPIRE`：设置或续期 7 天 TTL。

默认配置：

```dotenv
REDIS_URL=redis://127.0.0.1:6379/0
CONTEXT_CACHE_TTL_SECONDS=604800
```

## 缓存一致性与降级

### 缓存命中

直接将 List 中的每轮 JSON 展开为两条 LLM 历史消息，不查询 MySQL 历史。

### 缓存未命中或内容损坏

1. 从 MySQL 查询同一会话最近 N 轮。
2. 构造 LLM 历史。
3. 使用 `replace_cache()` 完整重建 Redis。
4. 继续对话，不因为缓存未命中而失败。

### Redis 不可用

1. 捕获 Redis 连接、读取或写入异常。
2. 从 MySQL 加载历史并继续主流程。
3. 不把 Redis 连接异常直接抛给 Unity。
4. 记录需要重新校准的会话，避免恢复后读到故障前的旧缓存。
5. 后续成功从 MySQL 重建后，再恢复正常 Redis 读取。

Redis 故障可能影响性能和历史来源，但不应删除 MySQL 记录，也不应让文字对话凭空消失。

## 会话与记忆边界

### 同一连接

- 建连时生成一个 UUID `session_id`。
- 同一连接的所有请求共享该 ID。
- 上下文历史依次为 0、1、2……轮。
- 达到 10 轮后保持最近 10 轮，最旧轮次逐步淘汰。

### 断线重连

- 新连接生成新的 `session_id`。
- 新会话历史从 0 轮开始。
- 旧会话完整记录仍保留在 MySQL。
- 旧 Redis 数据可能仍在 TTL 内，但不会自动并入新会话。
- 跨重连恢复最近会话属于后续版本，不属于 v0.2 的已实现能力。

## 管理后台链路

| 页面或功能 | FastAPI 接口 | 数据来源与副作用 |
| --- | --- | --- |
| 健康状态 | `GET /api/health` | 检查 API、MySQL 和 Redis |
| 读取启用人设 | `GET /api/personas/active` | 读取 MySQL |
| 保存启用人设 | `PUT /api/personas/active` | 校验并更新 MySQL |
| 对话日志 | `GET /api/conversations` | 分页、Session ID 和情绪筛选 |
| 情绪统计 | `GET /api/conversations/emotion-stats` | 对完整记录分组统计 |
| 音色试听 | `POST /api/tts/preview` | 调用 Edge TTS 并返回临时 MP3 |

音色试听遵守以下边界：

- 使用独立临时音频文件；
- 只允许白名单音色；
- 响应结束后删除临时文件；
- 不改变 Unity 对话的默认音色；
- 不写入对话记录；
- 不影响当前会话上下文。

对话统计针对当前用户的完整记录，不受日志分页影响。翻页不需要重新统计，执行查询或重置时再刷新统计。

## 错误隔离

Pipeline 使用阶段错误区分：

- `ASR`：音频识别失败或没有识别出内容；
- `DB`：用户、人设、历史或对话入库失败；
- `LLM`：DeepSeek 请求失败；
- `TTS`：语音合成失败。

WebSocket 服务将阶段错误转换为协议错误码，数据库错误对应 `DB_FAILED`。网络操作使用有限重试，单次异常不应导致整个服务进程退出。

每轮 TTS 使用独立 UUID 文件名，避免并发请求共同覆盖 `reply.mp3`。

## 当前非目标

v0.2 暂不包含：

- 登录、JWT、角色权限和公网安全管理；
- 跨连接自动恢复会话；
- 向量检索和长期语义记忆；
- 真实情绪识别；
- 正式数据库迁移工具；
- Docker、CI 和微服务拆分。

这些能力应在保持当前主链路稳定的前提下按版本逐步加入。