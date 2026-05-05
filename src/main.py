import argparse
import json
import logging
import os
from typing import Any

from src.normalize.config import QwenConfig
from src.normalize.data_loader import load_dataset
from src.normalize.inference import create_engine

logger = logging.getLogger(__name__)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def _non_negative_limit(value: str) -> int | None:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("limit must be >= 0")
    return parsed or None


def _sample_to_text(sample: Any) -> str:
    if isinstance(sample, str):
        return sample
    if isinstance(sample, dict):
        for key in ("text", "comment", "content", "original"):
            value = sample.get(key)
            if isinstance(value, str):
                return value
    return json.dumps(sample, ensure_ascii=False)


def _build_parser() -> argparse.ArgumentParser:
    defaults = QwenConfig()
    parser = argparse.ArgumentParser(description="Normalize Vietnamese comments with Qwen.")
    parser.add_argument("--dataset-path", default=defaults.dataset_path)
    parser.add_argument("--output-path", default=defaults.output_path)
    parser.add_argument("--model-name", default=defaults.model_name)
    parser.add_argument("--api-base-url", default=defaults.api_base_url)
    parser.add_argument("--api-key-env", default=defaults.api_key_env)
    parser.add_argument("--limit", type=_non_negative_limit, default=defaults.limit)
    parser.add_argument("--batch-size", type=_positive_int, default=defaults.batch_size)
    parser.add_argument("--max-concurrent", type=_positive_int, default=defaults.max_concurrent)
    parser.add_argument("--temperature", type=float, default=defaults.temperature)
    parser.add_argument("--enable-thinking", action="store_true", default=defaults.enable_thinking)
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    config = QwenConfig(
        model_name=args.model_name,
        api_base_url=args.api_base_url,
        api_key_env=args.api_key_env,
        enable_thinking=args.enable_thinking,
        temperature=args.temperature,
        max_concurrent=args.max_concurrent,
        batch_size=args.batch_size,
        limit=args.limit,
        dataset_path=args.dataset_path,
        output_path=args.output_path,
    )

    samples = load_dataset(config.dataset_path)
    comments = [_sample_to_text(sample) for sample in samples]
    if config.limit is not None:
        comments = comments[: config.limit]

    logger.info(
        "Loaded %s samples from %s; normalizing %s with %s",
        len(samples),
        config.dataset_path,
        len(comments),
        config.model_name,
    )

    engine = create_engine(config)
    predictions = engine.generate(comments)

    os.makedirs(os.path.dirname(config.output_path) or ".", exist_ok=True)
    with open(config.output_path, "w", encoding="utf-8") as f:
        for index, (comment, prediction) in enumerate(zip(comments, predictions)):
            record = {
                "index": index,
                "input": comment,
                "normalized": prediction.get("normalized"),
                "error": prediction.get("error"),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Saved %s records to %s", len(predictions), config.output_path)


if __name__ == "__main__":
    main()
