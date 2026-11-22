"""test_api_persona.py —— 验证人设 GET、UTF-8 PUT、参数校验与恢复"""
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"


def api_request(method: str, path: str, payload: dict | None = None):
    """发送明确编码为 UTF-8 的 JSON 请求。"""
    data = None
    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    original = api_request("GET", "/api/personas/active")

    assert original["name"].strip()
    assert original["content"].strip()

    test_content = (
        original["content"]
        + "\n- REST API 中文更新测试。"
    )

    try:
        updated = api_request(
            "PUT",
            "/api/personas/active",
            {
                "name": original["name"],
                "content": test_content,
            },
        )

        assert updated["content"] == test_content
        assert "中文更新测试" in updated["content"]
        assert "# 角色设定" in updated["content"]

        print("[通过] PUT 能正确保存和返回中文人设")

        # 只包含空白字符的内容必须返回 422
        try:
            api_request(
                "PUT",
                "/api/personas/active",
                {
                    "name": "Nagi",
                    "content": "   ",
                },
            )
            raise AssertionError("空白人设没有被 API 拒绝")

        except urllib.error.HTTPError as e:
            assert e.code == 422, (
                f"空白人设应返回 422，实际为 {e.code}"
            )

        print("[通过] 空白人设返回 HTTP 422")

    finally:
        # 无论断言成功或失败，都尽量恢复测试前的人设
        restored = api_request(
            "PUT",
            "/api/personas/active",
            {
                "name": original["name"],
                "content": original["content"],
            },
        )

        assert restored["content"] == original["content"]
        print("[恢复] 已恢复测试前的人设内容")

    print("[完成] 人设 API 全部测试通过")


if __name__ == "__main__":
    main()