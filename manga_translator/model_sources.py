from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urlparse

MODEL_SOURCES_ENV_VAR = "MODEL_SOURCES_PATH"
MODEL_SOURCES_FILENAME = "model_sources.toml"
DEFAULT_MODEL_SOURCE_STRATEGY = "official_first"
VALID_MODEL_SOURCE_STRATEGIES = {"official_first", "mirror_first", "custom"}
_MIRROR_HOSTS = {
    "modelscope.cn",
    "www.modelscope.cn",
    "hf-mirror.com",
    "www.hf-mirror.com",
}

_DEFAULT_MODEL_SOURCES_CONTENT = """version = 1

# 下载策略：
# - official_first: 内置标准源 -> 内置镜像源
# - mirror_first: 内置镜像源 -> 内置标准源
# - custom: custom.urls -> 内置标准源 -> 内置镜像源
strategy = \"official_first\"

# 可选：如果不想使用默认 examples/model_sources.toml，可在 .env 中指定外部文件：
# MODEL_SOURCES_PATH=/abs/path/to/model_sources.toml

# -----------------------------------------------------------------------------
# builtin.official / builtin.mirror 仅用于“查看当前仓库内置下载源”，属于只读参考。
# 程序不会从这些表读取 URL；真正的内置 official / mirror 仍然来自各模型类的 _MODEL_MAPPING。
# 如果你要自定义下载源，请只修改 [custom.urls]。
# -----------------------------------------------------------------------------

[builtin.official]
\"DefaultDetector:model\" = [
  \"https://github.com/zyddnys/manga-image-translator/releases/download/beta-0.3/detect-20241225.ckpt\",
]
\"ModelPaddleOCRVL:color_model\" = [
  \"https://github.com/zyddnys/manga-image-translator/releases/download/beta-0.3/ocr_ar_48px.ckpt\",
]
\"ModelPaddleOCRVL:color_dict\" = [
  \"https://github.com/zyddnys/manga-image-translator/releases/download/beta-0.3/alphabet-all-v7.txt\",
]
\"StableDiffusionInpainter:model_grapefruit\" = [
  \"https://civitai.com/api/download/models/8364\",
]
\"StableDiffusionInpainter:model_wd_swinv2\" = [
  \"https://huggingface.co/SmilingWolf/wd-v1-4-swinv2-tagger-v2/resolve/main/model.onnx\",
]
\"StableDiffusionInpainter:model_wd_swinv2_csv\" = [
  \"https://huggingface.co/SmilingWolf/wd-v1-4-swinv2-tagger-v2/resolve/main/selected_tags.csv\",
]

[builtin.mirror]
\"DefaultDetector:model\" = [
  \"https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/detect-20241225.ckpt\",
]
\"YOLOOBBDetector:model\" = [
  \"https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/ysgyolo_yolo26_2.0.pt\",
]
\"MangaLensBubbleDetector:model\" = [
  \"https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/mangalens.pt\",
]
\"ModelPaddleOCRVL:model\" = [
  \"https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/PaddleOCR-VL-1.5.7z\",
]
\"ModelPaddleOCRVL:color_model\" = [
  \"https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/ocr_ar_48px.ckpt\",
]
\"ModelPaddleOCRVL:color_dict\" = [
  \"https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/alphabet-all-v7.txt\",
]
\"StableDiffusionInpainter:model_wd_swinv2\" = [
  \"https://hf-mirror.com/SmilingWolf/wd-v1-4-swinv2-tagger-v2/resolve/main/model.onnx\",
]
\"StableDiffusionInpainter:model_wd_swinv2_csv\" = [
  \"https://hf-mirror.com/SmilingWolf/wd-v1-4-swinv2-tagger-v2/raw/main/selected_tags.csv\",
]

[custom.urls]
# key 形式：<wrapper_key>:<map_key>
# wrapper_key 来自 ModelWrapper 的 _key / 类名
# map_key 来自 _MODEL_MAPPING 的键
#
# 只有 strategy = \"custom\" 时才会优先使用。
# custom 的固定顺序为：
#   custom.urls[key] -> builtin official -> builtin mirror
#
# 如果某个 key 没写在这里，或自定义 URL 全部失败，
# 程序会自动回退到该 key 的内置 official_first 顺序。
#
# 可以按需取消注释并改成你自己的地址：
# \"DefaultDetector:model\" = [
#   \"https://your-storage.example.com/detect-20241225.ckpt\",
# ]
# \"ModelPaddleOCRVL:model\" = [
#   \"https://your-storage.example.com/PaddleOCR-VL-1.5.7z\",
# ]
# \"StableDiffusionInpainter:model_wd_swinv2\" = [
#   \"https://your-storage.example.com/model.onnx\",
# ]
"""


@dataclass(slots=True)
class ModelSourcesConfig:
    strategy: str = DEFAULT_MODEL_SOURCE_STRATEGY
    custom_urls: dict[str, list[str]] = field(default_factory=dict)
    path: str | None = None
    loaded_from_file: bool = False


class InvalidModelSourcesConfig(ValueError):
    pass


def _log(logger, level: str, message: str):
    if logger and hasattr(logger, level):
        getattr(logger, level)(message)


def _get_examples_dir() -> str:
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, "examples")
        return os.path.join(os.path.dirname(sys.executable), "examples")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "examples")


def get_default_model_sources_path() -> str:
    return os.path.join(_get_examples_dir(), MODEL_SOURCES_FILENAME)


def _normalize_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path.strip()))


def get_env_model_sources_path() -> str | None:
    raw_value = str(os.environ.get(MODEL_SOURCES_ENV_VAR, "") or "").strip()
    if not raw_value:
        return None
    return _normalize_path(raw_value)


def get_model_sources_candidate_paths(path: str | None = None) -> list[str]:
    candidates: list[str] = []
    if path:
        candidates.append(_normalize_path(path))
    else:
        env_path = get_env_model_sources_path()
        if env_path:
            candidates.append(env_path)
        candidates.append(get_default_model_sources_path())

    unique_candidates: list[str] = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def get_model_sources_path(path: str | None = None) -> str:
    return get_model_sources_candidate_paths(path)[0]


def ensure_model_sources_file(path: str | None = None, logger=None) -> str:
    config_path = get_model_sources_path(path)
    if os.path.exists(config_path):
        return config_path

    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as file:
        file.write(_DEFAULT_MODEL_SOURCES_CONTENT)

    _log(logger, "info", f"已创建模型下载源配置文件: {config_path}")
    return config_path


def _normalize_url_list(urls: Iterable[str], *, config_key: str) -> list[str]:
    normalized: list[str] = []
    for raw_url in urls:
        url = str(raw_url or "").strip()
        if not url:
            continue
        if not url.startswith(("http://", "https://")):
            raise InvalidModelSourcesConfig(f"{config_key} 中包含非法 URL: {url}")
        if url not in normalized:
            normalized.append(url)
    return normalized


def _parse_custom_urls(data: object) -> dict[str, list[str]]:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise InvalidModelSourcesConfig("custom.urls 必须是 TOML table")

    normalized: dict[str, list[str]] = {}
    for raw_key, raw_urls in data.items():
        key = str(raw_key or "").strip()
        if not key:
            raise InvalidModelSourcesConfig("custom.urls 中存在空键")
        if not isinstance(raw_urls, list):
            raise InvalidModelSourcesConfig(f"custom.urls[{key}] 必须是 URL 数组")
        normalized[key] = _normalize_url_list(raw_urls, config_key=f"custom.urls[{key}]")
    return normalized


def _load_model_sources_file(config_path: str) -> ModelSourcesConfig:
    with open(config_path, "rb") as file:
        payload = tomllib.load(file)

    version = payload.get("version", 1)
    if not isinstance(version, int) or version != 1:
        raise InvalidModelSourcesConfig(f"仅支持 version = 1，当前为: {version!r}")

    strategy = str(payload.get("strategy", DEFAULT_MODEL_SOURCE_STRATEGY) or "").strip()
    if strategy not in VALID_MODEL_SOURCE_STRATEGIES:
        raise InvalidModelSourcesConfig(f"strategy 必须是 {sorted(VALID_MODEL_SOURCE_STRATEGIES)} 之一")

    custom = payload.get("custom", {})
    if custom is None:
        custom = {}
    if not isinstance(custom, dict):
        raise InvalidModelSourcesConfig("custom 必须是 TOML table")

    custom_urls = _parse_custom_urls(custom.get("urls", {}))
    return ModelSourcesConfig(
        strategy=strategy,
        custom_urls=custom_urls,
        path=config_path,
        loaded_from_file=True,
    )


def load_model_sources_config(logger=None, path: str | None = None) -> ModelSourcesConfig:
    for candidate_path in get_model_sources_candidate_paths(path):
        try:
            config_path = ensure_model_sources_file(candidate_path, logger=logger)
            config = _load_model_sources_file(config_path)
            _log(logger, "info", f"已加载模型下载源配置: {config_path} (strategy={config.strategy})")
            return config
        except Exception as exc:
            _log(logger, "warning", f"加载模型下载源配置失败，回退到下一级来源: {candidate_path} ({exc})")

    _log(logger, "warning", "模型下载源配置不可用，回退到内置默认策略 official_first")
    return ModelSourcesConfig()


def _is_mirror_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    if hostname in _MIRROR_HOSTS:
        return True
    return "mirror" in hostname


def split_builtin_urls(urls: str | Iterable[str]) -> tuple[list[str], list[str]]:
    builtin_urls = urls if isinstance(urls, list) else [urls] if isinstance(urls, str) else list(urls)
    normalized = _normalize_url_list(builtin_urls, config_key="builtin urls")

    official_urls: list[str] = []
    mirror_urls: list[str] = []
    for url in normalized:
        if _is_mirror_url(url):
            mirror_urls.append(url)
        else:
            official_urls.append(url)
    return official_urls, mirror_urls


def resolve_candidate_urls(
    source_id: str,
    builtin_urls: str | Iterable[str],
    logger=None,
    path: str | None = None,
) -> list[str]:
    config = load_model_sources_config(logger=logger, path=path)
    official_urls, mirror_urls = split_builtin_urls(builtin_urls)

    candidate_urls: list[str] = []
    if config.strategy == "mirror_first":
        candidate_urls.extend(mirror_urls)
        candidate_urls.extend(official_urls)
    elif config.strategy == "custom":
        candidate_urls.extend(config.custom_urls.get(source_id, []))
        candidate_urls.extend(official_urls)
        candidate_urls.extend(mirror_urls)
    else:
        candidate_urls.extend(official_urls)
        candidate_urls.extend(mirror_urls)

    return _normalize_url_list(candidate_urls, config_key=f"resolved candidates[{source_id}]")
