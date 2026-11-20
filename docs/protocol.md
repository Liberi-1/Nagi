# Nagi 对话协议 v0.1

## 1. 传输层

- 基于 WebSocket，默认地址 `ws://localhost:8765`。
- 每条消息为**单个二进制帧**，帧内结构：

  | 部分 | 长度 | 说明 |
  |---|---|---|
  | 头长度 | 4 字节 | JSON 头的 UTF-8 字节数 N，大端序无符号整数 |
  | JSON 头 | N 字节 | UTF-8 编码的 JSON 对象 |
  | 音频负载 | 帧内剩余字节 | 原始音频文件字节；无音频时为空 |

## 2. 消息类型

### 2.1 chat_request（客户端 → 服务端）

JSON 头字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| type | string | 固定 `"chat_request"` |
| request_id | string | 客户端生成的唯一 ID（如 UUID），用于配对请求与响应 |
| audio_format | string | 录音格式，v0.1 固定 `"wav"` |
| sample_rate | int | 采样率，建议 16000 |

负载：用户录音的完整 WAV 文件字节。

### 2.2 chat_response（服务端 → 客户端）

JSON 头字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| type | string | 固定 `"chat_response"` |
| request_id | string | 与对应请求一致 |
| text | string | 角色回复文本 |
| emotion | string | 情绪标签，v0.1 固定 `"neutral"` |
| audio_format | string | 回复音频格式，v0.1 固定 `"mp3"` |

负载：回复音频的完整 MP3 文件字节。

### 2.3 error（服务端 → 客户端）

JSON 头字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| type | string | 固定 `"error"` |
| request_id | string | 与对应请求一致；请求无法解析时可为空字符串 |
| code | string | 错误码，见第 3 节 |
| message | string | 人类可读的错误描述（中文） |

负载：无。

## 3. 错误码

| code | 含义 |
|---|---|
| BAD_REQUEST | 消息结构或字段不合法 |
| ASR_FAILED | 语音识别失败 |
| LLM_FAILED | 回复生成失败 |
| TTS_FAILED | 语音合成失败 |
| TIMEOUT | 处理超时 |
| INTERNAL | 其他服务端异常 |

## 4. 一次完整往返示例

```
客户端 → [头长度][{"type":"chat_request","request_id":"a1b2","audio_format":"wav","sample_rate":16000}][WAV 字节]
服务端 → [头长度][{"type":"chat_response","request_id":"a1b2","text":"你好呀","emotion":"neutral","audio_format":"mp3"}][MP3 字节]
```