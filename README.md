# Nagi

开源、可定制的端到端虚拟角色平台：

**语音输入 → ASR 语音识别 → LLM 生成回复 → TTS 语音合成 → Unity 播放语音并切换动画。**

&gt; 当前状态：v0.2 数据层与 Web 管理后台已完成。支持 MySQL 对话持久化、Redis 最近上下文缓存、同一连接多轮对话、人设在线编辑、日志分页筛选、音色试听和情绪统计。

## 功能特性

### 实时语音对话

- **语音对话闭环**：Whisper 本地识别 → DeepSeek 生成回复 → Edge TTS 合成语音 → Unity 播放回应。
- **多轮上下文**：同一 WebSocket 连接默认携带最近 10 轮对话，每轮包含一条用户输入和一条角色回复。
- **Unity 客户端**：按键录音、WebSocket 通信、语音播放，以及 Idle／Talking 动画自动切换。
- **协议兼容**：保留 v0.1 请求方式，响应新增的 `session_id` 可由旧客户端忽略。
- **健壮性**：分层错误码、处理超时、网络操作有限重试；Redis 故障时自动回退 MySQL。

### 数据与人设管理

- **MySQL 持久化**：保存用户、人设和完整对话记录。
- **Redis 上下文缓存**：缓存同一会话最近 N 轮对话，默认 TTL 为 7 天。
- **数据库人设**：管理后台读取和修改当前启用人设，保存后由后续对话使用。
- **初始化导入**：首次初始化时可从 `backend/config/persona.md` 导入人设，之后以 MySQL 中的内容为准。

### Web 管理后台

- 人设读取、编辑、校验和未保存修改保护。
- 对话日志分页、Session ID 筛选和情绪筛选。
- 展开查看完整用户输入、角色回复、Session ID 和 Request ID。
- Edge TTS 多音色试听，不修改 Unity 默认音色，也不写入对话记录。
- 对话情绪数量、百分比和总数统计。
- MySQL、Redis 和 API 健康状态展示。

## 整体结构

```text
Unity 客户端
    │ WebSocket
    ▼
backend/server.py
    │
    ▼
backend/pipeline.py
    ├── Whisper ASR
    ├── MySQL：用户、人设、完整对话记录
    ├── Redis：当前会话最近 N 轮上下文
    ├── DeepSeek LLM
    └── Edge TTS

Vue 管理后台
    │ HTTP
    ▼
backend/api.py
    ├── 人设管理
    ├── 对话分页与筛选
    ├── 情绪统计
    └── TTS 试听
```

WebSocket 协议详见 [docs/protocol.md](docs/protocol.md)。

## 环境要求

当前主要在 Windows 本地开发和验证：

- Python 3.12
- MySQL 8
- Memurai Developer，或其他兼容 Redis 协议的服务
- Node.js LTS 与 npm
- FFmpeg：`winget install Gyan.FFmpeg`，安装后重新打开终端
- DeepSeek API Key
- Unity 2022.3 LTS，仅在运行客户端时需要

v0.2 不要求 Docker。

## 后端安装

### 1. 克隆仓库并创建虚拟环境

```powershell
git clone https://github.com/Liberi-1/Nagi.git
cd Nagi

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果提示禁止运行脚本，可执行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

然后重新激活虚拟环境。

### 2. 安装 Python 依赖

```powershell
cd backend

# --extra-index-url 用于安装 CPU 版 PyTorch
python -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

首次运行 Whisper 时会自动下载 base 模型，约 140 MB。

### 3. 准备 MySQL 数据库

启动 MySQL 服务后，可以使用 root 账号创建开发数据库和专用账号：

```sql
CREATE DATABASE nagi
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER 'nagi'@'localhost'
    IDENTIFIED BY 'your_local_password';

GRANT ALL PRIVILEGES ON nagi.*
    TO 'nagi'@'localhost';
```

请将自己的本地密码同步填写到 `backend/.env` 的 `DATABASE_URL` 中。

### 4. 配置环境变量

在 `backend/` 目录执行：

```powershell
copy .env.example .env
```

编辑 `backend/.env`：

```dotenv
DEEPSEEK_API_KEY=填写自己的Key
DATABASE_URL=mysql+pymysql://nagi:your_local_password@localhost:3306/nagi?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:6379/0
CONTEXT_CACHE_TTL_SECONDS=604800
```

真实 `.env` 不应提交到 Git。

确保 Memurai 或 Redis 协议兼容服务已启动，并监听 `127.0.0.1:6379`。

### 5. 初始化数据表和默认人设

```powershell
python init_db.py
```

初始化会创建数据表、默认本地用户，并在没有启用人设时从 `backend/config/persona.md` 导入。

重复执行不会重复创建默认用户，也不会使用文件覆盖数据库中已存在的人设。

## 启动开发环境

需要分别保持三个服务运行。

### 窗口 A：FastAPI 管理接口

```powershell
cd backend
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

地址：`http://127.0.0.1:8000`

### 窗口 B：WebSocket 对话服务

```powershell
cd backend
python server.py
```

地址：`ws://localhost:8765`

### 窗口 C：Vue 管理后台

首次运行：

```powershell
cd web-admin
copy .env.example .env.local
npm install
npm run dev
```

后续只需：

```powershell
cd web-admin
npm run dev
```

打开：`http://localhost:5173`

`.env.local` 默认内容：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

真实 `.env.local` 不应提交到 Git。

前端生产构建：

```powershell
cd web-admin
npm run build
```

## Unity 客户端

1. 先启动 FastAPI 和 WebSocket 后端服务。
2. Unity Hub → **Add project from disk**，选择本仓库的 `client-unity/` 目录。
3. 首次打开时，按 [docs/unity-assets.md](docs/unity-assets.md) 下载 Mixamo 角色和 Idle／Talking 动画，分别放入 `Assets/Models/` 与 `Assets/Animations/`。
4. 打开 `Assets/Scenes/Main.unity`，点击 **Play**。
5. 按 **R** 开始录音，再按 **R** 停止并发送。

收到回复后，角色会自动播放语音并切换到 Talking 动画，播放结束后回到 Idle。

角色资源的 `.meta` 已随仓库提供，文件名与路径保持一致即可恢复场景引用。Mixamo FBX 文件不提交到仓库，下载和使用时应遵守对应资源授权。

## 自定义角色

v0.2 推荐通过管理后台的「人设配置」页面修改名称和人设内容。

保存成功后，后续新对话会从 MySQL 读取最新启用人设，无需修改 Python 代码。

`backend/config/persona.md` 现在主要用于**首次初始化导入**，不再是运行期间的权威数据源。直接修改该文件不会覆盖数据库中已有的人设。

## 当前记忆机制

v0.2 的记忆分为两层：

| 层级 | 当前行为 |
| --- | --- |
| LLM 短期上下文 | 同一 WebSocket 会话最近 10 轮 |
| Redis 缓存 | 保存当前会话最近 10 轮，默认 TTL 为 7 天 |
| MySQL 对话记录 | 保存完整历史，不随上下文裁剪而删除 |

每轮对话包含：

```text
一条用户输入 + 一条角色回复
```

超过 10 轮后，最早的一轮不再发送给 LLM，但仍可在管理后台的完整日志中查询。

当前每次 WebSocket 建连都会生成新的 `session_id`。因此：

- 同一连接内可以进行多轮对话；
- 重连后会开启新会话，旧会话上下文不会自动恢复；
- 旧对话仍保留在 MySQL 和网页日志中；
- 跨重连恢复最近会话计划在后续版本实现。

## 自动化测试

在 `backend/` 目录、已激活虚拟环境，并确保 MySQL 和 Memurai 正常运行后执行核心回归：

```powershell
python test_repositories.py
python test_llm_context.py
python test_context_cache.py
python test_pipeline_context.py
python test_ws_session.py
```

其中：

- `test_llm_context.py` 默认不调用真实 DeepSeek；只有显式使用 `--live` 才会发起在线请求。
- `test_pipeline_context.py` 模拟 ASR、LLM 和 TTS，连续验证四轮上下文、MySQL 入库和 Redis 累积。
- `test_context_cache.py` 会主动模拟 Redis 故障，测试期间出现超时和回退日志属于预期行为。

保持 FastAPI 服务运行后，可执行接口测试：

```powershell
python test_api_persona.py
python test_api_conversations.py
python test_api_emotion_stats.py
python test_api_tts.py
```

`test_api_tts.py` 会实际调用 Edge TTS，需要外部网络。

## 目录结构

```text
client-unity/       Unity 客户端：录音、WebSocket、语音播放与动画切换
backend/            Python 后端
├── api.py          FastAPI 管理接口
├── server.py       WebSocket 对话服务
├── pipeline.py     ASR → 上下文 → LLM → 入库 → TTS
├── models.py       SQLAlchemy 数据模型
├── repositories.py 数据访问层
├── context_cache.py Redis 最近上下文缓存
└── config/         首次初始化使用的人设文件
web-admin/          Vue 3 + TypeScript 管理后台
docs/               需求、架构、协议、Unity 资源和开发日志
```

## 路线图

- **v0.1** 最小闭环：语音对话数字人（已完成）
- **v0.2** 数据层与 Web 管理后台：MySQL、Redis、多轮上下文、REST API、Vue 管理页面（已完成）
- **v0.3** 会话恢复与角色表现：跨重连恢复最近会话、表情、动作和特效
- **v0.4** 工程化：Docker、CI、正式数据库迁移和部署
- **v0.5** AI 进阶：本地模型、情绪识别和长期记忆
- **v1.0** 完整版：安全、权限和发布能力

## 已知限制

- 当前是本地单用户设计，管理接口没有登录、鉴权和权限控制，不应直接暴露到公网。
- 多轮上下文默认只包含同一会话最近 10 轮，不等同于完整长期记忆。
- WebSocket 重连后创建新会话，暂不支持自动恢复旧会话。
- 情绪标签目前仍固定为 `neutral`，统计页面展示的是现有记录中的标签分布。
- 数据表通过 SQLAlchemy `create_all` 初始化，尚未引入正式数据库迁移工具。
- LLM 是否正确使用已提供的历史仍具有概率性，数据层传递成功不代表每次回答都理想。
- Edge TTS 依赖外部网络，部分网络环境可能需要调整代理或更换网络。
- 中文识别模式下，英文专名可能被音译，例如 Nagi 可能被识别为其他中文写法。
- 当前版本不以公网部署为目标，Docker 和 CI 留待后续工程化阶段。

## License

MIT