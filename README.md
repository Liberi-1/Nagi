# Nagi

端到端可交互虚拟角色平台：语音输入 → ASR 语音识别 → LLM 生成回复 → TTS 语音合成 → Unity 角色带表情动作回应。

**开源、可定制**：通过编辑人设文件，任何人都可以让 Nagi 变成自己想要的角色。

&gt; 当前状态：v0.1 开发中。后端最小闭环已完成（命令行 Pipeline + WebSocket 服务），Unity 客户端开发中。

## 功能特性

- **语音对话闭环**：Whisper 本地识别 → DeepSeek 生成回复 → Edge TTS 合成语音
- **自定义人设**：编辑 `backend/config/persona.md` 即可定制角色性格，保存即生效，无需改代码
- **WebSocket 服务**：消息协议见 [docs/protocol.md](docs/protocol.md)，便于接入任意客户端
- **健壮性**：分层错误码、处理超时、网络错误有限重试，异常不会导致服务崩溃

## 快速开始（后端）

### 环境要求

- Windows（其他平台尚未测试）
- Python 3.12
- FFmpeg：`winget install Gyan.FFmpeg`（装完重开终端）
- DeepSeek API Key（自行申请，免费额度即可跑通）

### 安装

```powershell
git clone https://github.com/Liberi-1/Nagi.git
cd Nagi\backend

# 创建并激活虚拟环境
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
# 若提示"禁止运行脚本"，先执行：
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 安装依赖（--extra-index-url 用于安装 CPU 版 PyTorch）
python -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# 配置 API Key：复制模板并填入自己的 key
copy .env.example .env
# 用编辑器打开 .env，填入 DEEPSEEK_API_KEY=sk-...
```

### 验证

```powershell
# 命令行管线：音频进、音频出
python test_pipeline.py

# 或启动 WebSocket 服务，用测试客户端对话
python server.py            # 窗口 A，保持运行
python test_ws_client.py    # 窗口 B（同样需先激活 venv）
```

首次运行 Whisper 会自动下载 base 模型（约 140 MB），之后离线可用。

## 自定义你的角色

用编辑器打开 `backend/config/persona.md`，修改性格、说话方式和规则，保存即生效。
示例人设是一个安静温和、有点怕生的虚拟伙伴 Nagi，你可以把她改成任何样子。

## 目录结构

```
client-unity/    Unity 客户端（v0.1 开发中）
backend/         Python 后端：ASR / LLM / TTS / Pipeline / WebSocket 服务
docs/            需求、协议（protocol.md）、开发日志（devlog/）
web-admin/       Web 管理后台（v0.2 规划）
```

## 角色资源说明

本仓库不包含 Mixamo 角色与动画文件。如需运行 Unity 客户端，请自行前往
[Mixamo](https://www.mixamo.com) 下载：人形角色（FBX Binary、With Skin、T-pose）
及 Idle、Talking 两段动画（30fps，不携带模型）。

## 路线图

- **v0.1** 最小闭环：语音对话数字人（进行中）
- **v0.2** 数据层 + Web 管理后台（人设网页配置、对话记录）
- **v0.3** 图形升级：表情、动作、特效
- **v0.4** 工程化：测试、Docker、CI
- **v0.5** AI 进阶：本地模型、情绪识别、长期记忆
- **v1.0** 完整版：微服务、安全、发布

## 已知限制（v0.1）

- 单轮对话，多轮上下文将在 v0.2 加入
- 情绪标签固定为 neutral，情绪系统将在 v0.3 加入
- 中文识别模式下，英文专名可能被音译（如 Nagi → 奈迪），不影响对话理解

## License

MIT