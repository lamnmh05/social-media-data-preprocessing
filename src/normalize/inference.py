import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from openai import OpenAI
from tqdm import tqdm

from src.normalize.config import QwenConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Bạn là hệ thống chuẩn hóa văn bản tiếng Việt phi chuẩn trên mạng xã hội.

Nhiệm vụ của bạn là chuyển các comment tiếng Việt phi chuẩn về tiếng Việt chuẩn, đúng chính tả và giữ nguyên ý nghĩa gốc.

Bạn cần xử lý các hiện tượng sau:

1. Sai chính tả ở âm đầu hoặc âm cuối:
- péo -> béo
- kao -> cao
- vỡn -> giỡn
- zui -> vui
- chời -> trời

2. Dùng từ tiếng Anh hoặc từ có phát âm gần giống tiếng Việt để thay thế:
- bé bar -> bé ba
- horse hoảng -> hốt hoảng
- vì sound -> vì sao

3. Thay vần tiếng Việt bằng vần/từ tiếng Anh có âm gần giống:
- đỉnh kout -> đỉnh cao
- ngol -> ngon

4. Các hiện tượng cần tiền xử lý trước khi chuẩn hóa:
- Viết kéo dài để biểu đạt cảm xúc: nhaaa -> nha, màaaa -> mà
- Lỗi gõ Telex: hoaf -> hòa, ddawng -> đăng
- Viết dính liền: khongbiet -> không biết, ratngon -> rất ngon

Quy tắc bắt buộc:
- Chỉ chuẩn hóa những phần phi chuẩn.
- Giữ nguyên ý nghĩa, sắc thái cảm xúc, emoji, emoticon và từ thô tục nếu có.
- Không tự ý thêm thông tin mới.
- Không giải thích.
- Không dùng markdown.
- Output phải là JSON array gồm string.
- Số phần tử output phải bằng số phần tử input và giữ nguyên thứ tự.
""".strip()


def create_engine(config: QwenConfig) -> "QwenInference":
    return QwenInference(config)


def _read_dotenv(path: str = ".env") -> dict[str, str]:
    env_path = Path(path)
    if not env_path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _resolve_api_key(primary_env: str) -> str:
    env_names = []
    for name in (primary_env, "DASHSCOPE_API_KEY", "API_KEY"):
        if name and name not in env_names:
            env_names.append(name)

    for name in env_names:
        value = os.getenv(name)
        if value:
            return value

    dotenv_values = _read_dotenv()
    for name in env_names:
        value = dotenv_values.get(name)
        if value:
            return value

    raise RuntimeError(
        "Missing API key. Set DASHSCOPE_API_KEY or API_KEY in the environment or .env file."
    )


def _build_user_prompt(comments: list[str]) -> str:
    input_json = json.dumps(comments, ensure_ascii=False, indent=2)

    return f"""
Hãy chuẩn hóa từng comment trong JSON array đầu vào.

Examples:
Input:
[
  "tr chời nay zui vãi, péo lên hẳn",
  "đừng vỡn nữa, kao mệt rồi",
  "bé bar nhìn horse hoảng ghê",
  "vì sound bạn lại làm vậy",
  "quả này đỉnh kout thật sự",
  "món này ngol quá nhaaa",
  "okay bae yeahhhhh",
  "hoaf bình mới ddawng bài",
  "tui khongbiet sao món này ratngon",
  "vcl hôm nay mệt, lol"
]
Output:
[
  "trời ơi nay vui vãi, béo lên hẳn",
  "đừng giỡn nữa, tao mệt rồi",
  "bé ba nhìn hốt hoảng ghê",
  "vì sao bạn lại làm vậy"
  "quả này đỉnh cao thật sự",
  "món này ngon quá nha",
  "okay bae yeahhhhh",
  "hòa bình mới đăng bài",
  "tui không biết sao món này rất ngon",
  "vcl hôm nay mệt, lol"
]


Bây giờ hãy chuẩn hóa JSON array sau.

Input:
{input_json}

Output:
""".strip()



def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _extract_json_array(text: str) -> list[Any]:
    cleaned = _strip_code_fence(text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[[\s\S]*\]", cleaned)
    if not match:
        raise ValueError("Model output does not contain a JSON array.")

    data = json.loads(match.group(0))
    if not isinstance(data, list):
        raise ValueError("Parsed model output is not a JSON array.")
    return data


class QwenInference:
    """Batch normalization through DashScope's OpenAI-compatible chat API."""

    def __init__(self, config: QwenConfig):
        self.config = config
        self.client = OpenAI(
            base_url=config.api_base_url,
            api_key=_resolve_api_key(config.api_key_env),
        )

    def generate(self, comments: list[str]) -> list[dict[str, str | None]]:
        batches = [
            (start, comments[start : start + self.config.batch_size])
            for start in range(0, len(comments), self.config.batch_size)
        ]
        return self._run_concurrent(batches)

    def _call_batch(
        self, batch_id: int, batch: tuple[int, list[str]]
    ) -> tuple[int, list[dict[str, str | None]]]:
        start_index, comments = batch
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(comments)},
            ]
            raw_text, _thinking = self._chat(messages)
            normalized = _extract_json_array(raw_text)

            if len(normalized) != len(comments):
                raise ValueError(
                    f"Output length mismatch: expected {len(comments)}, got {len(normalized)}"
                )

            records = []
            for value in normalized:
                if not isinstance(value, str):
                    raise ValueError("Model output array must contain only strings.")
                records.append({"normalized": value, "error": None})
            return batch_id, records

        except Exception as exc:
            logger.warning("Batch starting at index %s failed: %s", start_index, exc)
            error = str(exc)
            return batch_id, [
                {"normalized": None, "error": error}
                for _ in comments
            ]

    def _chat(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        stream = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=self.config.temperature,
            stream=True,
            extra_body={"enable_thinking": self.config.enable_thinking},
        )

        answer_parts: list[str] = []
        thinking_parts: list[str] = []

        for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            reasoning_content = getattr(delta, "reasoning_content", None)
            content = getattr(delta, "content", None)

            if reasoning_content:
                thinking_parts.append(reasoning_content)
            if content:
                answer_parts.append(content)

        return "".join(answer_parts), "".join(thinking_parts)

    def _run_concurrent(
        self, batches: list[tuple[int, list[str]]]
    ) -> list[dict[str, str | None]]:
        batch_results: list[list[dict[str, str | None]] | None] = [None] * len(batches)

        with ThreadPoolExecutor(max_workers=self.config.max_concurrent) as executor:
            futures = {
                executor.submit(self._call_batch, batch_id, batch): batch_id
                for batch_id, batch in enumerate(batches)
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Normalizing",
                unit="batch",
            ):
                batch_id, records = future.result()
                batch_results[batch_id] = records

        flattened: list[dict[str, str | None]] = []
        for records in batch_results:
            if records:
                flattened.extend(records)
        return flattened
