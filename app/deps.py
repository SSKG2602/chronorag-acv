from __future__ import annotations

""" import sys uncomment while running in collab"""
import os
import warnings
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict

import yaml
from dotenv import load_dotenv

from app.light_mode import light_mode_enabled

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

warnings.filterwarnings("ignore", message="`torch_dtype` is deprecated", category=UserWarning)
warnings.filterwarnings("ignore", message="Valid config keys have changed in V2", category=UserWarning)

if not light_mode_enabled():
    try:  # pragma: no cover
        from transformers.utils import logging as hf_logging  # type: ignore

        hf_logging.set_verbosity_error()
    except Exception:  # pragma: no cover
        pass

from core.dhqc.controller import DHQCController
from core.retrieval.reranker_ce import CEReranker
from core.router.temporal_router import TemporalRouter
from storage.cache.redis_client import CacheClient
from storage.pvdb.dao import PVDB

ROOT = Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> Dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@dataclass
class AppState:
    pvdb: PVDB
    cache: CacheClient
    models_cfg: Dict
    policy_cfg: Dict
    axis_cfg: Dict
    tenant_cfg: Dict
    router: TemporalRouter
    controller: DHQCController
    reranker: CEReranker
    policy_version: str
    policy_applied_keys: set[str] = field(default_factory=set)


@lru_cache(maxsize=1)
def get_app_state() -> AppState:
    load_dotenv(ROOT / ".env")
    models_cfg = _load_yaml(ROOT / "config" / "models.yaml")
    policy_cfg = _load_yaml(ROOT / "config" / "polar.yaml")
    axis_cfg = _load_yaml(ROOT / "config" / "axis_policy.yaml")
    tenant_cfg = _load_yaml(ROOT / "config" / "tenants" / "default.yaml")

    pvdb = PVDB(models_cfg, persist_path=ROOT / "storage" / "pvdb" / "persisted.json")
    cache = CacheClient(os.getenv("REDIS_URL"))
    router = TemporalRouter(policy_cfg, axis_cfg, tenant_cfg)
    controller = DHQCController(policy_cfg.get("dhqc", {}))
    reranker = CEReranker(models_cfg.get("reranker", {}).get("name", "bge-reranker-base"))
    return AppState(
        pvdb=pvdb,
        cache=cache,
        models_cfg=models_cfg,
        policy_cfg=policy_cfg,
        axis_cfg=axis_cfg,
        tenant_cfg=tenant_cfg,
        router=router,
        controller=controller,
        reranker=reranker,
        policy_version=policy_cfg.get("policy_version", "v0"),
    )


def get_models_cfg() -> Dict:
    return get_app_state().models_cfg


def get_policy_cfg() -> Dict:
    return get_app_state().policy_cfg


def set_policy_cfg(new_policy: Dict, version: str, idempotency_key: str | None = None) -> None:
    state = get_app_state()
    if idempotency_key and idempotency_key in state.policy_applied_keys:
        return
    state.policy_cfg.update(new_policy)
    state.policy_version = version
    if idempotency_key:
        state.policy_applied_keys.add(idempotency_key)


def get_pvdb() -> PVDB:
    return get_app_state().pvdb


def get_router() -> TemporalRouter:
    return get_app_state().router


def get_controller() -> DHQCController:
    return get_app_state().controller


def get_reranker() -> CEReranker:
    return get_app_state().reranker


def get_cache() -> CacheClient:
    return get_app_state().cache


"""ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))""" """ uncomment while running in collab"""
