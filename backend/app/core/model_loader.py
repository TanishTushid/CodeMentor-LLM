"""Validate and load the base model with its local PEFT adapter."""

import json
import logging
from typing import Any

from app.config import Settings
from app.core.inference import InferenceEngine

logger = logging.getLogger(__name__)


class ModelLoadError(RuntimeError):
    """Raised when the base model or local adapter cannot be loaded."""


class ModelLoader:
    """Load one base model and attach the configured local LoRA adapter."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _read_adapter_config(self) -> dict[str, Any]:
        """Validate adapter files and return the observed PEFT configuration."""
        config_path = self.settings.adapter_path / "adapter_config.json"
        weights_path = self.settings.adapter_path / "adapter_model.safetensors"
        if not config_path.is_file() or not weights_path.is_file():
            raise ModelLoadError(
                "The configured adapter directory must contain adapter_config.json "
                "and adapter_model.safetensors."
            )
        try:
            with config_path.open(encoding="utf-8") as adapter_file:
                adapter_config = json.load(adapter_file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelLoadError("The adapter configuration could not be read.") from exc

        if adapter_config.get("peft_type") != "LORA":
            raise ModelLoadError("The configured adapter is not a LoRA adapter.")
        if adapter_config.get("task_type") != "CAUSAL_LM":
            raise ModelLoadError("The configured adapter is not for a causal language model.")
        adapter_base = adapter_config.get("base_model_name_or_path")
        if adapter_base != self.settings.model_name:
            raise ModelLoadError(
                "The adapter's recorded base model does not match MODEL_NAME."
            )
        return adapter_config

    def load(self) -> InferenceEngine:
        """Load tokenizer, base model, and adapter once for application startup."""
        self._read_adapter_config()
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer

            device, dtype = self._select_device(torch)
            tokenizer = AutoTokenizer.from_pretrained(
                self.settings.model_name,
                trust_remote_code=False,
            )
            model = AutoModelForCausalLM.from_pretrained(
                self.settings.model_name,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
                trust_remote_code=False,
            )
            model = PeftModel.from_pretrained(
                model,
                self.settings.adapter_path,
                is_trainable=False,
            )
            model.to(device)
            model.eval()
            logger.info("Loaded model %s with its local LoRA adapter on %s", self.settings.model_name, device)
            return InferenceEngine(
                model=model,
                tokenizer=tokenizer,
                device=device,
                max_input_tokens=self.settings.max_input_tokens,
            )
        except ModelLoadError:
            raise
        except Exception as exc:
            logger.exception("Model initialization failed")
            raise ModelLoadError(
                "The model could not be initialized. Check server logs for details."
            ) from exc

    def _select_device(self, torch: Any) -> tuple[Any, Any]:
        """Use CUDA only when the device can safely run this model in FP16."""
        requested = self.settings.device.casefold()
        if requested not in {"auto", "cpu", "cuda"}:
            raise ModelLoadError("DEVICE must be one of: auto, cpu, cuda.")
        if requested == "cpu":
            return torch.device("cpu"), torch.float32

        if torch.cuda.is_available():
            capability = torch.cuda.get_device_capability()
            if capability >= (7, 0):
                return torch.device("cuda"), torch.float16
            logger.warning(
                "CUDA device capability %s is below the supported FP16 threshold; using CPU.",
                capability,
            )
        elif requested == "cuda":
            logger.warning("CUDA was requested but is unavailable; using CPU.")

        return torch.device("cpu"), torch.float32
