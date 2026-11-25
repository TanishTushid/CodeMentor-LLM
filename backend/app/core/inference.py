"""Reusable, chat-template-aware generation engine."""

import logging
import threading
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.prompts import SYSTEM_PROMPTS

logger = logging.getLogger(__name__)


class InferenceError(RuntimeError):
    """Raised when tokenization or model generation fails."""


class InferenceEngine:
    """Run serialized inference against one loaded causal language model."""

    def __init__(
        self,
        *,
        model: Any,
        tokenizer: Any,
        device: Any,
        max_input_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.max_input_tokens = max_input_tokens
        self._generation_lock = threading.Lock()

    @property
    def device_name(self) -> str:
        """Return the device as a safe string for health responses."""
        return str(self.device)

    def generate(
        self,
        prompt: str,
        *,
        task_type: str = "general",
        language: str | None = None,
        history: Sequence[Mapping[str, str]] | None = None,
        generation_options: Mapping[str, Any] | None = None,
    ) -> str:
        """Generate a response using the tokenizer's Qwen chat template."""
        if task_type not in SYSTEM_PROMPTS:
            raise ValueError(f"Unsupported task type: {task_type}")

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPTS[task_type]}
        ]
        if history:
            messages.extend(
                {"role": message["role"], "content": message["content"]}
                for message in history
            )
        messages.append({"role": "user", "content": prompt})

        try:
            encoded = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            )
            input_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
            if input_ids.shape[-1] > self.max_input_tokens:
                input_ids = input_ids[:, -self.max_input_tokens :]
                if isinstance(encoded, Mapping):
                    encoded["input_ids"] = input_ids
                    if "attention_mask" in encoded:
                        encoded["attention_mask"] = encoded["attention_mask"][
                            :, -self.max_input_tokens :
                        ]
            if isinstance(encoded, Mapping):
                encoded = {
                    key: value.to(self.device) if hasattr(value, "to") else value
                    for key, value in encoded.items()
                }
            else:
                encoded = {"input_ids": input_ids.to(self.device)}

            options = dict(generation_options or {})
            max_new_tokens = int(options.get("max_new_tokens", 512))
            do_sample = bool(options.get("do_sample", False))
            generation_kwargs: dict[str, Any] = {
                "max_new_tokens": max_new_tokens,
                "do_sample": do_sample,
                "repetition_penalty": float(options.get("repetition_penalty", 1.05)),
                "eos_token_id": self.tokenizer.eos_token_id,
                "pad_token_id": self.tokenizer.pad_token_id,
            }
            if do_sample:
                generation_kwargs["temperature"] = float(options.get("temperature", 0.7))
                generation_kwargs["top_p"] = float(options.get("top_p", 0.9))

            import torch

            with self._generation_lock, torch.inference_mode():
                output = self.model.generate(**encoded, **generation_kwargs)

            prompt_length = encoded["input_ids"].shape[-1]
            answer = self.tokenizer.decode(
                output[0][prompt_length:],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            ).strip()
            if not answer:
                raise InferenceError("The model returned an empty response.")
            return answer
        except InferenceError:
            raise
        except Exception as exc:
            logger.exception("Inference failed for task %s", task_type)
            raise InferenceError("The model could not generate a response.") from exc
