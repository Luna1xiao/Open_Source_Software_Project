"""LLM 客户端 - 封装 API 调用"""

import http.client
import json
import os
import ssl
from dataclasses import dataclass
from pathlib import Path


def _candidate_env_paths() -> list[Path]:
    home = Path.home()
    return [
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
        home / ".mercury" / ".env",
        home / ".mercury" / "agent_summary.env",
    ]


def _load_env():
    """加载 .env 文件"""
    for env_path in _candidate_env_paths():
        if not env_path.exists():
            continue
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


# 启动时加载 .env
_load_env()


@dataclass
class LLMResponse:
    """LLM 响应"""
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMClientError(Exception):
    """Raised when the upstream LLM provider rejects or malforms a response."""

    def __init__(self, detail: str, status_code: int | None = None):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class LLMClient:
    """LLM 客户端"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "https://chat.ecnu.edu.cn/open/api/v1")
        self.model = model or os.environ.get("LLM_MODEL", "ecnu-max")

        # 提取主机名
        self.host = self.base_url.replace("https://", "").replace("http://", "").split("/")[0]
        # 提取路径前缀
        self.path_prefix = "/" + "/".join(self.base_url.split("/")[3:])

    async def chat(self, prompt: str) -> str:
        """发送聊天请求，返回文本"""
        response = await self.chat_with_usage(prompt)
        return response.text

    async def chat_with_usage(self, prompt: str) -> LLMResponse:
        """发送聊天请求，返回带用量的响应"""
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
        }

        context = ssl.create_default_context()
        conn = http.client.HTTPSConnection(self.host, context=context)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        conn.request(
            "POST",
            f"{self.path_prefix}/chat/completions",
            body=json.dumps(data).encode("utf-8"),
            headers=headers,
        )

        response = conn.getresponse()
        raw_body = response.read().decode("utf-8", errors="replace")
        conn.close()

        try:
            resp_data = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError as exc:
            raise LLMClientError("LLM provider returned invalid JSON.", status_code=response.status) from exc

        if response.status >= 400:
            detail = _extract_error_detail(resp_data) or f"LLM provider request failed ({response.status})."
            raise LLMClientError(f"LLM provider rejected the request: {detail}", status_code=response.status)

        try:
            text = _extract_message_text(resp_data)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMClientError("LLM provider returned an unexpected response format.", status_code=response.status) from exc

        usage = resp_data.get("usage", {})

        return LLMResponse(
            text=text,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )


def _extract_error_detail(payload: dict) -> str | None:
    detail = payload.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()

    error = payload.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip()
    if isinstance(error, dict):
        for key in ("message", "detail", "code"):
            value = error.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_message_text(payload: dict) -> str:
    choices = payload["choices"]
    first_choice = choices[0]
    content = first_choice["message"]["content"]

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
        joined = "".join(part for part in text_parts if part)
        if joined:
            return joined

    raise ValueError("Unsupported message content shape")
