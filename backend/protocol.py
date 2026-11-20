"""protocol.py —— 消息协议编解码：4 字节头长度 + JSON 头 + 音频负载"""
import json
import struct


def pack_message(header: dict, payload: bytes = b"") -> bytes:
    """把 JSON 头和音频字节打包成一个二进制帧。"""
    header_bytes = json.dumps(header, ensure_ascii=False).encode("utf-8")
    return struct.pack(">I", len(header_bytes)) + header_bytes + payload


def unpack_message(frame: bytes) -> tuple[dict, bytes]:
    """把二进制帧拆成 JSON 头和音频字节。"""
    n = struct.unpack(">I", frame[:4])[0]
    header = json.loads(frame[4:4 + n].decode("utf-8"))
    payload = frame[4 + n:]
    return header, payload