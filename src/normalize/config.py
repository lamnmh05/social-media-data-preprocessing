from dataclasses import dataclass

@dataclass
class QwenConfig:
    model_name: str = "qwen3-235b-a22b-instruct-2507"
    api_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    api_key_env: str = "API_KEY"
   
    enable_thinking: bool = True
    temperature: float = 0.0

    max_concurrent: int = 2
    batch_size: int = 10
    limit: int | None = 100

    dataset_path: str = "src/data/filtered/filtered_data.json"
    output_path: str = "outputs/normalized_filtered_data_test100_2.jsonl"
