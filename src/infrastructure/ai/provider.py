from __future__ import annotations

from application.ai.contracts import AIProvider
from infrastructure.ai.local_transformers import LocalTransformersAIProvider
from infrastructure.config.settings import AIConfig


def build_ai_provider(config: AIConfig) -> AIProvider:
    return LocalTransformersAIProvider(
        configured_model_id=config.effective_model_id,
        model_path=config.local_model_path,
        cache_dir=config.local_cache_dir,
        torch_cache_dir=config.local_torch_cache_dir,
        torch_kernel_cache_dir=config.local_torch_kernel_cache_dir,
        device=config.local_device,
        dtype=config.local_dtype,
        max_input_tokens=config.local_max_input_tokens,
        max_concurrent_requests=config.local_max_concurrent_requests,
        top_p=config.local_top_p,
        repetition_penalty=config.local_repetition_penalty,
        trust_remote_code=config.local_trust_remote_code,
    )
