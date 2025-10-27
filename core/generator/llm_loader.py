"""Pluggable LLM backend loader supporting local and remote execution modes."""

from typing import Protocol, List, Dict, Optional
import os

import httpx
import logging


class LLMBackend(Protocol):
    def generate(
        self,
        messages: List[Dict],
        max_tokens: int,
        temperature: float,
        stop: Optional[list] = None,
    ) -> str:
        ...

logger = logging.getLogger(__name__)


class OpenAICompat:
    def __init__(self, endpoint: str, api_key: str, model: str):
        self.endpoint, self.api_key, self.model = endpoint, api_key, model

    def generate(self, messages, max_tokens, temperature, stop=None) -> str:
        """Invoke any OpenAI-compatible /chat/completions endpoint."""
        if not self.endpoint or not self.api_key:
            raise RuntimeError("OpenAI-compatible not configured")
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if stop:
            payload["stop"] = stop
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = httpx.post(
            f"{self.endpoint}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class LightningAIBackend:
    def __init__(self, base_url: str, api_key: str, model: str):
        if not base_url or not api_key:
            raise RuntimeError("Lightning AI backend not configured")
        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("openai package is required for Lightning AI backend") from exc

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def generate(self, messages, max_tokens, temperature, stop=None) -> str:
        # Lightning's GPT-5 endpoint ignores OpenAI max_tokens; rely on stop markers and post-processing.
        kwargs = {}
        if stop:
            kwargs["stop"] = stop
        response = self.client.chat.completions.create(model=self.model, messages=messages, **kwargs)
        message = response.choices[0].message
        content = getattr(message, "content", "") or ""
        if isinstance(content, list):
            # Reasoning models can return structured segments; concatenate text fragments.
            text = []
            for chunk in content:
                if isinstance(chunk, dict):
                    text.append(chunk.get("text") or "")
                else:
                    text.append(str(chunk))
            content = "".join(text)
        return str(content)


class LlamaCppBackend:
    def __init__(self, gguf_path: str, n_ctx: int = 4096, n_gpu_layers: int = -1):
        from llama_cpp import Llama  # local import

        self.llm = Llama(
            model_path=gguf_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )

    def generate(self, messages, max_tokens, temperature, stop=None) -> str:
        out = self.llm.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop or [],
        )
        return out["choices"][0]["message"]["content"]


class OllamaBackend:
    def __init__(self, model: str, host: str = "http://localhost:11434"):
        self.model, self.host = model, host

    def generate(self, messages, max_tokens, temperature, stop=None) -> str:
        response = httpx.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "stop": stop or [],
                },
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


class LocalHFBackend:
    def __init__(
        self,
        model_path: str,
        dtype: str = "bfloat16",
        device_map: Optional[str] = "auto",
        load_in_4bit: bool = False,
        bnb_4bit_compute_dtype: Optional[str] = None,
        trust_remote_code: bool = True,
        token_env: Optional[str] = None,
    ):
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore[import]
        import torch

        if hasattr(torch, dtype):
            torch_dtype = getattr(torch, dtype)
        else:
            torch_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        hf_token = None
        if token_env:
            candidate = os.getenv(token_env)
            if candidate:
                hf_token = candidate
        token_kwargs = {}
        if hf_token:
            token_kwargs = {"token": hf_token, "use_auth_token": hf_token}
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=trust_remote_code,
            **token_kwargs,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        model_kwargs = {
            "device_map": device_map,
            "trust_remote_code": trust_remote_code,
        }
        if load_in_4bit:
            compute_dtype = bnb_4bit_compute_dtype or ("float16" if torch.cuda.is_available() else "float32")
            compute_attr = getattr(torch, compute_dtype, torch.float16)
            model_kwargs.update(
                {
                    "load_in_4bit": True,
                    "bnb_4bit_compute_dtype": compute_attr,
                }
            )
        else:
            model_kwargs["torch_dtype"] = torch_dtype
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                **model_kwargs,
                **token_kwargs,
            )
        except Exception:
            if load_in_4bit:
                # Fallback to standard precision when 4-bit loading is unavailable.
                model_kwargs.pop("load_in_4bit", None)
                model_kwargs.pop("bnb_4bit_compute_dtype", None)
                model_kwargs["torch_dtype"] = torch_dtype
                logger.warning("4-bit load failed for %s; retrying with standard precision", model_path)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    **model_kwargs,
                    **token_kwargs,
                )
            else:
                raise

    def generate(self, messages, max_tokens, temperature, stop=None) -> str:
        import torch

        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        gen_kwargs = {
            "max_new_tokens": max_tokens,
            "temperature": max(temperature, 1e-5),
            "do_sample": temperature > 0,
        }
        outputs = self.model.generate(
            **inputs,
            **gen_kwargs,
            use_cache=False,
            pad_token_id=self.tokenizer.pad_token_id,
        )
        completion = outputs[0][inputs["input_ids"].shape[1]:]
        text = self.tokenizer.decode(completion, skip_special_tokens=True).strip()
        if stop:
            for token in stop:
                if token in text:
                    text = text.split(token)[0]
        return text


def load_backend(cfg) -> tuple[LLMBackend, str]:
    """Return the first working backend defined by the strategy order."""
    order = cfg["strategy_order"]
    for name in order:
        try:
            if name == "lightning_ai":
                entry = cfg["lightning_ai"]
                base_url = entry.get("base_url") or ""
                api_key_env = entry.get("api_key_env")
                api_key_default = entry.get("api_key_default")
                api_key = ""
                if api_key_env:
                    api_key = os.getenv(api_key_env, "")
                if not api_key and api_key_default:
                    api_key = api_key_default
                model = entry.get("model", "openai/gpt-5")
                if base_url and api_key:
                    return LightningAIBackend(base_url, api_key, model), "lightning_ai"
            elif name == "openai_compat":
                entry = cfg["openai_compat"]
                endpoint = os.getenv(entry["endpoint_env"] or "")
                api_key = os.getenv(entry["api_key_env"] or "")
                if endpoint and api_key:
                    return OpenAICompat(endpoint, api_key, entry["model"]), "openai_compat"
            elif name == "local_hf":
                entry = cfg["local_hf"]
                path = entry.get("model_path")
                allow_remote = entry.get("allow_remote", False)
                if path and (os.path.exists(path) or allow_remote):
                    backend = LocalHFBackend(
                        path,
                        entry.get("dtype", "bfloat16"),
                        entry.get("device_map", "auto"),
                        entry.get("load_in_4bit", False),
                        entry.get("bnb_4bit_compute_dtype"),
                        entry.get("trust_remote_code", True),
                        entry.get("token_env"),
                    )
                    return backend, "local_hf"
            elif name == "llama_cpp":
                entry = cfg["llama_cpp"]
                path = entry["gguf_path"]
                if os.path.exists(path):
                    return LlamaCppBackend(path, entry["n_ctx"], entry["n_gpu_layers"]), "llama_cpp"
            elif name == "ollama":
                entry = cfg["ollama"]
                return OllamaBackend(entry["model"], entry["host"]), "ollama"
        except Exception:
            logger.exception("LLM backend '%s' unavailable", name)
            continue
    raise RuntimeError("No LLM backend available")
