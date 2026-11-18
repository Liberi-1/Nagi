# Nagi

Nagi 是一个交互式数字人项目：用户对着麦克风说话，后端依次完成语音识别、大语言模型生成回复和语音合成，Unity 中的 3D 角色会带着表情和动作开口回答。项目从最小闭环出发，逐步加入数据库、Web 后台、图形特效、工程化和 AI 进阶功能。

## 架构图

（待补充，完成后放在 `docs/` 下）

## 路线图

- [ ] v0.1 最小闭环：语音 → 文本 → LLM → 语音，Unity 角色播放
- [ ] v0.2 数据层 + Web 后台
- [ ] v0.3 图形、动画、特效
- [ ] v0.4 工程化
- [ ] v0.5 AI 进阶
- [ ] v1.0 完整版

## 技术栈

- 客户端：Unity、C#
- 后端：Python、WebSocket
- AI：Whisper（语音识别）、LLM、TTS
- 数据：MySQL、Redis
- Web 后台：Vue
- 工程化：Docker、GitHub Actions、pytest

## 目录结构

```
client-unity/   # Unity 工程
backend/        # Python 后端
web-admin/      # Vue 后台
docs/           # 需求、架构图、接口文档
docs/devlog/    # 每版本开发日志
```

## 运行方法

TBD