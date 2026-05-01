from __future__ import annotations

import asyncio
import logging
import os
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from application.ai.contracts import AIMessage, AIProviderError

logger = logging.getLogger(__name__)

_JSON_ONLY_INSTRUCTIONS = (
    "Return strictly valid JSON only. Do not use Markdown. "
    "Do not include prose before or after the JSON object."
)


@dataclass(slots=True)
class _LocalTransformersRuntime:
    tokenizer: Any
    model: Any
    torch: Any
    device: str


@dataclass(slots=True, frozen=True)
class LocalTransformersStatus:
    provider: str
    model_id: str
    model_path: str | None
    loaded: bool
    device: str
    dtype: str
    cache_dir: str
    max_input_tokens: int
    max_concurrent_requests: int


@dataclass(slots=True)
class LocalTransformersAIProvider:
    configured_model_id: str
    model_path: Path | None
    cache_dir: Path = Path("/cache/huggingface")
    torch_cache_dir: Path = Path("/cache/torch")
    torch_kernel_cache_dir: Path = Path("/cache/torch_kernels")
    device: str = "auto"
    dtype: str = "auto"
    max_input_tokens: int = 4096
    max_concurrent_requests: int = 1
    top_p: float = 0.9
    repetition_penalty: float = 1.05
    trust_remote_code: bool = False
    _runtime: _LocalTransformersRuntime | None = field(default=None, init=False, repr=False)
    _runtime_lock: threading.Lock = field(
        default_factory=threading.Lock,
        init=False,
        repr=False,
    )
    _semaphore: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(max(1, self.max_concurrent_requests))

    @property
    def is_enabled(self) -> bool:
        return True

    @property
    def model_id(self) -> str | None:
        if self.model_path is not None:
            return str(self.model_path)
        return self.configured_model_id

    @property
    def is_loaded(self) -> bool:
        return self._runtime is not None

    @property
    def status(self) -> LocalTransformersStatus:
        runtime = self._runtime
        return LocalTransformersStatus(
            provider="local",
            model_id=self.configured_model_id,
            model_path=str(self.model_path) if self.model_path is not None else None,
            loaded=runtime is not None,
            device=runtime.device if runtime is not None else self.device,
            dtype=self.dtype,
            cache_dir=str(self.cache_dir),
            max_input_tokens=self.max_input_tokens,
            max_concurrent_requests=self.max_concurrent_requests,
        )

    async def load(self) -> None:
        await asyncio.to_thread(self._ensure_runtime)

    async def complete(
        self,
        *,
        messages: Sequence[AIMessage],
        max_output_tokens: int,
        temperature: float,
        expect_json: bool = False,
    ) -> str:
        async with self._semaphore:
            prepared_messages = tuple(messages)
            if expect_json:
                prepared_messages = _apply_json_constraints(prepared_messages)
            return await asyncio.to_thread(
                self._complete_blocking,
                prepared_messages,
                max(1, max_output_tokens),
                max(0.0, temperature),
            )

    def _complete_blocking(
        self,
        messages: tuple[AIMessage, ...],
        max_output_tokens: int,
        temperature: float,
    ) -> str:
        runtime = self._ensure_runtime()
        try:
            inputs = self._build_inputs(runtime=runtime, messages=messages)
            input_token_count = int(inputs["input_ids"].shape[-1])
            generation_kwargs = self._build_generation_kwargs(
                runtime=runtime,
                inputs=inputs,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            )
            with runtime.torch.inference_mode():
                generated = runtime.model.generate(**generation_kwargs)
            new_tokens = generated[0][input_token_count:]
            completion = runtime.tokenizer.decode(new_tokens, skip_special_tokens=True)
        except AIProviderError:
            raise
        except Exception as exc:  # pragma: no cover - exact backend errors depend on torch.
            if _is_out_of_memory_error(exc):
                raise AIProviderError(
                    "Local AI generation ran out of memory.",
                    failure_category="local_out_of_memory",
                ) from exc
            raise AIProviderError(
                "Local AI generation failed.",
                failure_category="local_generation_failed",
            ) from exc

        cleaned = _clean_completion(completion)
        if not cleaned:
            raise AIProviderError(
                "Local AI provider returned an empty response.",
                failure_category="local_generation_failed",
            )
        return cleaned

    def _ensure_runtime(self) -> _LocalTransformersRuntime:
        runtime = self._runtime
        if runtime is not None:
            return runtime

        with self._runtime_lock:
            runtime = self._runtime
            if runtime is None:
                runtime = self._load_runtime()
                self._runtime = runtime
            return runtime

    def _load_runtime(self) -> _LocalTransformersRuntime:
        _configure_cache_environment(
            cache_dir=self.cache_dir,
            torch_cache_dir=self.torch_cache_dir,
            torch_kernel_cache_dir=self.torch_kernel_cache_dir,
        )
        if self.model_path is not None and not self.model_path.exists():
            raise AIProviderError(
                "Local AI model path does not exist.",
                failure_category="local_model_not_found",
            )
        try:
            import torch  # type: ignore[import-not-found]
            from transformers import (  # type: ignore[import-not-found]
                AutoModelForCausalLM,
                AutoTokenizer,
            )
        except ImportError as exc:
            raise AIProviderError(
                "Local AI provider requires torch and transformers to be installed.",
                failure_category="local_model_load_failed",
            ) from exc

        model_ref = (
            str(self.model_path) if self.model_path is not None else self.configured_model_id
        )
        logger.info(
            "Loading local AI model provider=local model_id=%s device=%s dtype=%s",
            self.model_id,
            self.device,
            self.dtype,
        )
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_ref,
                cache_dir=str(self.cache_dir),
                trust_remote_code=self.trust_remote_code,
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_ref,
                cache_dir=str(self.cache_dir),
                torch_dtype=_resolve_torch_dtype(torch=torch, dtype=self.dtype),
                trust_remote_code=self.trust_remote_code,
            )
            _ensure_pad_token(tokenizer=tokenizer, model=model)
            resolved_device = _resolve_device(torch=torch, configured_device=self.device)
            model.to(resolved_device)
            model.eval()
        except Exception as exc:
            if _is_out_of_memory_error(exc):
                raise AIProviderError(
                    "Local AI model load ran out of memory.",
                    failure_category="local_out_of_memory",
                ) from exc
            if _is_model_not_found_error(exc):
                raise AIProviderError(
                    "Local AI model was not found.",
                    failure_category="local_model_not_found",
                ) from exc
            raise AIProviderError(
                "Local AI model failed to load.",
                failure_category="local_model_load_failed",
            ) from exc
        logger.info(
            "Loaded local AI model provider=local model_id=%s resolved_device=%s",
            self.model_id,
            resolved_device,
        )
        return _LocalTransformersRuntime(
            tokenizer=tokenizer,
            model=model,
            torch=torch,
            device=resolved_device,
        )

    def _build_inputs(
        self,
        *,
        runtime: _LocalTransformersRuntime,
        messages: tuple[AIMessage, ...],
    ) -> dict[str, Any]:
        rendered_prompt = _render_prompt(runtime.tokenizer, messages)
        inputs = runtime.tokenizer(
            rendered_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        )
        return {
            key: value.to(runtime.device) if hasattr(value, "to") else value
            for key, value in dict(inputs).items()
        }

    def _build_generation_kwargs(
        self,
        *,
        runtime: _LocalTransformersRuntime,
        inputs: dict[str, Any],
        max_output_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        pad_token_id = getattr(runtime.tokenizer, "pad_token_id", None)
        if pad_token_id is None:
            pad_token_id = getattr(runtime.tokenizer, "eos_token_id", None)

        generation_kwargs: dict[str, Any] = {
            **inputs,
            "max_new_tokens": max_output_tokens,
            "do_sample": temperature > 0,
            "pad_token_id": pad_token_id,
        }
        eos_token_id = getattr(runtime.tokenizer, "eos_token_id", None)
        if eos_token_id is not None:
            generation_kwargs["eos_token_id"] = eos_token_id
        if temperature > 0:
            generation_kwargs["temperature"] = temperature
            generation_kwargs["top_p"] = self.top_p
        if self.repetition_penalty != 1:
            generation_kwargs["repetition_penalty"] = self.repetition_penalty
        return generation_kwargs


def _configure_cache_environment(
    *,
    cache_dir: Path,
    torch_cache_dir: Path,
    torch_kernel_cache_dir: Path,
) -> None:
    os.environ["HF_HOME"] = str(cache_dir)
    os.environ["TRANSFORMERS_CACHE"] = str(cache_dir)
    os.environ["TORCH_HOME"] = str(torch_cache_dir)
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = str(torch_kernel_cache_dir)
    os.environ["TRITON_CACHE_DIR"] = str(torch_kernel_cache_dir)


def _resolve_torch_dtype(*, torch: Any, dtype: str) -> Any:
    if dtype == "auto":
        return "auto"
    return {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }[dtype]


def _resolve_device(*, torch: Any, configured_device: str) -> str:
    normalized = configured_device.strip().lower()
    if normalized and normalized != "auto":
        return normalized
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(getattr(torch, "backends", None), "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _ensure_pad_token(*, tokenizer: Any, model: Any) -> None:
    pad_token_id = getattr(tokenizer, "pad_token_id", None)
    if pad_token_id is None and getattr(tokenizer, "eos_token", None) is not None:
        tokenizer.pad_token = tokenizer.eos_token
        pad_token_id = getattr(tokenizer, "pad_token_id", None)
    if pad_token_id is None:
        pad_token_id = getattr(tokenizer, "eos_token_id", None)
    if pad_token_id is not None and getattr(model, "generation_config", None) is not None:
        model.generation_config.pad_token_id = pad_token_id


def _render_prompt(tokenizer: Any, messages: tuple[AIMessage, ...]) -> str:
    chat_messages = [{"role": message.role, "content": message.content} for message in messages]
    apply_chat_template = getattr(tokenizer, "apply_chat_template", None)
    if callable(apply_chat_template):
        try:
            rendered = apply_chat_template(
                chat_messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except (TypeError, ValueError):
            rendered = None
        if isinstance(rendered, str) and rendered.strip():
            return rendered

    lines: list[str] = []
    for message in messages:
        role = "System" if message.role == "system" else "User"
        lines.append(f"{role}: {message.content.strip()}")
    lines.append("Assistant:")
    return "\n\n".join(lines)


def _apply_json_constraints(messages: tuple[AIMessage, ...]) -> tuple[AIMessage, ...]:
    if not messages:
        return (AIMessage(role="system", content=_JSON_ONLY_INSTRUCTIONS),)
    first, *rest = messages
    if first.role == "system":
        return (
            AIMessage(
                role="system",
                content=f"{first.content.strip()}\n\n{_JSON_ONLY_INSTRUCTIONS}",
            ),
            *rest,
        )
    return (AIMessage(role="system", content=_JSON_ONLY_INSTRUCTIONS), *messages)


def _clean_completion(raw: str) -> str:
    text = raw.strip()
    for prefix in ("assistant:", "assistant\n", "Assistant:", "Assistant\n"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
    return text


def _is_out_of_memory_error(exc: Exception) -> bool:
    text = f"{exc.__class__.__name__} {exc}".lower()
    return "outofmemory" in text or "out of memory" in text or "cuda oom" in text


def _is_model_not_found_error(exc: Exception) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    text = str(exc).lower()
    return "not found" in text or "does not exist" in text or "no such file" in text
