# Nagi Web 管理后台

Nagi v0.2 的本地管理界面，基于 Vue 3、TypeScript、Vite 和 Vue Router。

它用于管理实时语音对话产生的数据，不是网页端数字人客户端。Unity 实时对话仍由 `backend/server.py` 提供 WebSocket 服务。

## 功能页面

### 人设配置

- 读取 MySQL 中当前启用的人设；
- 编辑人设名称和内容；
- 非空与长度校验；
- 显示未保存状态、保存进度、成功和错误反馈；
- 保存失败后保留当前输入；
- 重新读取或离开页面前提示未保存修改。

### 对话日志

- 分页查看 MySQL 中的完整对话；
- 按 Session ID 和情绪筛选；
- 修改每页数量；
- 展开完整用户输入、角色回复、Session ID 和 Request ID；
- 点击表格中的简短 Session ID 快速筛选整个会话；
- 查看情绪数量、百分比和总数统计。

情绪统计针对完整记录，不受当前分页影响。当前实时链路的情绪仍固定为 `neutral`。

### 音色试听

- 选择 FastAPI 白名单中的 Edge TTS 音色；
- 输入试听文本并生成 MP3；
- 在浏览器中播放结果；
- 新试听和组件卸载时释放旧 Object URL。

试听不会修改 Unity 默认音色，不会写入对话记录，也不会影响当前多轮上下文。

## 环境要求

- Node.js LTS
- npm
- 已启动的 Nagi FastAPI 管理接口
- 人设和日志功能需要 MySQL
- 音色试听需要 FastAPI 能访问 Edge TTS 外部服务

Redis 不是页面启动的硬性依赖，但健康状态会显示其是否可用。实时语音对话在 Redis 不可用时应回退 MySQL。

## 配置 API 地址

首次运行时，在 `web-admin/` 目录复制环境变量模板：

```powershell
copy .env.example .env.local
```

默认配置：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

如果修改了 `.env.local`，需要重启 Vite 开发服务器。

真实 `.env.local` 不应提交到 Git。

## 启动后端管理接口

在另一个终端中执行：

```powershell
cd backend
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

保持该窗口运行。

FastAPI 与 Unity 使用的 WebSocket 服务是两个独立进程。只使用管理后台时，可以不启动 Unity；但人设、日志等接口仍需要 MySQL 正常运行。

## 安装与启动

在 `web-admin/` 目录执行：

```powershell
npm install
npm run dev
```

打开：

```text
http://localhost:5173
```

`npm run dev` 启动后会一直保持运行，不继续输出大量日志属于正常现象。不要关闭该窗口。

## 页面路由

项目使用 Hash 路由：

| 页面 | 地址 |
| --- | --- |
| 人设配置 | `http://localhost:5173/#/persona` |
| 对话日志 | `http://localhost:5173/#/conversations` |
| 音色试听 | `http://localhost:5173/#/voice` |

访问根路径时会自动跳转到人设配置。

使用 Hash 路由可以避免本地静态预览时，刷新子页面需要服务器额外配置重写规则。

## 生产构建

```powershell
cd web-admin
npm run build
```

构建产物位于：

```text
web-admin/dist/
```

`npm run build` 只负责检查 TypeScript、Vue SFC 并生成静态文件，不会启动开发服务器。

## 主要结构

```text
web-admin/
├── src/
│   ├── App.vue                    侧栏、健康状态和路由出口
│   ├── main.ts                    Vue 应用入口
│   ├── router/index.ts            Hash 路由
│   ├── lib/api.ts                 API 类型、请求和错误格式化
│   ├── views/
│   │   ├── PersonaView.vue        人设读取与编辑
│   │   ├── ConversationsView.vue  日志分页、筛选和情绪统计
│   │   └── VoicePreviewView.vue   Edge TTS 音色试听
│   ├── style.css                  全局样式与响应式布局
│   └── vite-env.d.ts              Vite 与 Vue SFC 类型声明
├── .env.example                   环境变量模板
└── package.json                   npm 脚本和前端依赖
```

## API 请求约定

`src/lib/api.ts` 统一处理：

- `VITE_API_BASE_URL`；
- JSON 请求与响应；
- FastAPI `detail` 校验错误格式化；
- 人设、日志、统计和健康状态类型；
- TTS 试听的 Blob 响应。

TTS 试听返回音频文件，因此不能按普通 JSON 解析。

## 常见问题

### 打开 `localhost:5173` 显示连接被拒绝

通常是没有启动 Vite，或者开发服务器窗口已被关闭。

在 `web-admin/` 目录执行：

```powershell
npm run dev
```

不要只执行 `npm run build`。

### 页面能打开，但接口请求失败

检查：

1. FastAPI 是否在 `127.0.0.1:8000` 运行；
2. `.env.local` 中的 `VITE_API_BASE_URL` 是否正确；
3. 修改环境变量后是否重启 Vite；
4. MySQL 是否正常运行；
5. FastAPI 窗口是否出现具体异常。

### 在 backend 中执行 npm 后提示找不到 package.json

npm 命令应在 `web-admin/` 中执行：

```powershell
cd ..\web-admin
npm run dev
```

Python 服务在 `backend/` 中运行，Git 操作在仓库根目录执行。

### 修改页面后浏览器仍显示旧内容

先确认源文件已经保存，再检查终端是否出现编译错误。必要时在浏览器按 `Ctrl+F5` 强制刷新。

如果整个路由页面空白，检查：

- `src/router/index.ts` 是否注册路由；
- `App.vue` 是否有对应导航；
- 组件文件名和导入路径是否一致；
- 浏览器控制台和 Vite 终端是否有异常。

### VS Code 提示找不到 `.vue` 模块

确认 `src/vite-env.d.ts` 存在，并包含 Vite 客户端和 Vue SFC 声明。

可以重启 TypeScript Server，使用 Vue - Official 扩展，并避免同时启用旧 Vetur 造成冲突。

### 试听失败

试听依赖真实 Edge TTS 外部网络。检查 FastAPI 日志、网络连接和代理设置。

试听失败不应影响人设和日志页面，也不应修改已有对话数据。

## 当前边界

- 本地单用户管理后台，无登录和权限控制；
- 不应直接暴露到公网；
- 对话情绪当前固定为 `neutral`；
- 管理后台不能恢复旧 WebSocket 会话的实时上下文；
- 重连后的会话恢复属于后续版本功能。