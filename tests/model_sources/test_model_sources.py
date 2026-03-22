import asyncio
import hashlib
from pathlib import Path

import manga_translator.model_sources as model_sources
from manga_translator.utils.inference import ModelWrapper


def _write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_config(path: Path, *, strategy: str, custom_urls: dict[str, list[str]] | None = None):
    lines = [
        'version = 1',
        f'strategy = "{strategy}"',
        '',
        '[custom.urls]',
    ]
    for key, urls in (custom_urls or {}).items():
        url_list = ', '.join(f'"{url}"' for url in urls)
        lines.append(f'"{key}" = [{url_list}]')
    _write_text(path, '\n'.join(lines) + '\n')


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _BaseTestWrapper(ModelWrapper):
    _KEY = 'DummyWrapper'

    def __init__(self, model_root: Path, mapping: dict, *, key: str = 'DummyWrapper', temp_root: Path | None = None):
        self._MODEL_DIR = str(model_root)
        self._MODEL_MAPPING = mapping
        self._KEY = key
        super().__init__()
        if temp_root is not None:
            temp_root.mkdir(parents=True, exist_ok=True)
            self.__dict__['_temp_working_directory'] = str(temp_root)

    async def _load(self, device: str, *args, **kwargs):
        return None

    async def _unload(self):
        return None

    async def _infer(self, *args, **kwargs):
        return None


class _FileDownloadWrapper(_BaseTestWrapper):
    def __init__(self, *args, url_to_bytes: dict[str, bytes], **kwargs):
        self.url_to_bytes = url_to_bytes
        self.download_calls: list[str] = []
        super().__init__(*args, **kwargs)

    async def _download_file(self, url: str, path: str):
        self.download_calls.append(url)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.url_to_bytes[url])


class _ArchiveDownloadWrapper(_BaseTestWrapper):
    def __init__(self, *args, failing_urls: set[str], archive_relpath: str, **kwargs):
        self.failing_urls = set(failing_urls)
        self.archive_relpath = archive_relpath
        self.download_calls: list[str] = []
        self.last_download_url: str | None = None
        super().__init__(*args, **kwargs)

    async def _download_file(self, url: str, path: str):
        self.last_download_url = url
        self.download_calls.append(url)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'archive-bytes')

    def _extract_archive(self, download_path: str, extracted_path: str):
        if self.last_download_url in self.failing_urls:
            raise RuntimeError('archive extraction failed')
        target = Path(extracted_path) / self.archive_relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('archive-ok', encoding='utf-8')


def test_load_model_sources_uses_default_path_when_env_missing(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    monkeypatch.delenv(model_sources.MODEL_SOURCES_ENV_VAR, raising=False)
    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))

    config = model_sources.load_model_sources_config()

    assert config.strategy == 'official_first'
    assert config.loaded_from_file is True
    assert config.path == str(default_path)
    assert default_path.exists()


def test_env_model_sources_path_takes_priority_over_default(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    external_path = tmp_path / 'external' / 'model_sources.toml'
    _write_config(default_path, strategy='official_first')
    _write_config(external_path, strategy='mirror_first')

    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))
    monkeypatch.setenv(model_sources.MODEL_SOURCES_ENV_VAR, str(external_path))

    config = model_sources.load_model_sources_config()

    assert config.strategy == 'mirror_first'
    assert config.path == str(external_path)


def test_invalid_env_config_falls_back_to_default_path(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    external_path = tmp_path / 'external' / 'model_sources.toml'
    _write_config(default_path, strategy='mirror_first')
    _write_text(external_path, 'version = 2\nstrategy = "custom"\n')

    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))
    monkeypatch.setenv(model_sources.MODEL_SOURCES_ENV_VAR, str(external_path))

    config = model_sources.load_model_sources_config()

    assert config.strategy == 'mirror_first'
    assert config.path == str(default_path)


def test_strategy_order_and_single_source_degenerate_behavior(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))
    monkeypatch.delenv(model_sources.MODEL_SOURCES_ENV_VAR, raising=False)

    official_url = 'https://github.com/example/project/releases/download/v1/model.bin'
    mirror_url = 'https://www.modelscope.cn/models/example/project/resolve/master/model.bin'

    _write_config(default_path, strategy='official_first')
    assert model_sources.resolve_candidate_urls('DummyWrapper:model', [official_url, mirror_url]) == [official_url, mirror_url]

    _write_config(default_path, strategy='mirror_first')
    assert model_sources.resolve_candidate_urls('DummyWrapper:model', [official_url, mirror_url]) == [mirror_url, official_url]

    single_source = ['https://www.modelscope.cn/models/example/project/resolve/master/only.bin']
    for strategy in ('official_first', 'mirror_first', 'custom'):
        _write_config(default_path, strategy=strategy)
        assert model_sources.resolve_candidate_urls('DummyWrapper:model', single_source) == single_source


def test_custom_strategy_merges_and_deduplicates_urls(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))
    monkeypatch.delenv(model_sources.MODEL_SOURCES_ENV_VAR, raising=False)

    custom_url = 'https://custom.example.com/model.bin'
    official_url = 'https://github.com/example/project/releases/download/v1/model.bin'
    mirror_url = 'https://www.modelscope.cn/models/example/project/resolve/master/model.bin'
    _write_config(
        default_path,
        strategy='custom',
        custom_urls={
            'DummyWrapper:model': [custom_url, official_url],
        },
    )

    assert model_sources.resolve_candidate_urls('DummyWrapper:model', [official_url, mirror_url]) == [
        custom_url,
        official_url,
        mirror_url,
    ]
    assert model_sources.resolve_candidate_urls('DummyWrapper:missing', [official_url, mirror_url]) == [
        official_url,
        mirror_url,
    ]


def test_stable_filename_does_not_change_with_strategy_or_custom_url(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))
    monkeypatch.delenv(model_sources.MODEL_SOURCES_ENV_VAR, raising=False)

    builtin_official = 'https://github.com/example/project/releases/download/v1/detect-20241225.ckpt'
    builtin_mirror = 'https://www.modelscope.cn/models/example/project/resolve/master/detect-20241225.ckpt'
    mapping = {
        'model': {
            'url': [builtin_official, builtin_mirror],
            'file': '.',
        }
    }

    _write_config(default_path, strategy='mirror_first')
    mirror_first_wrapper = _BaseTestWrapper(tmp_path / 'models-mirror', mapping, key='DefaultDetector')
    mirror_first_path = Path(mirror_first_wrapper._get_resolved_file_path('model', mapping['model'])).name

    _write_config(
        default_path,
        strategy='custom',
        custom_urls={
            'DefaultDetector:model': ['https://custom.example.com/download?id=123'],
        },
    )
    custom_wrapper = _BaseTestWrapper(tmp_path / 'models-custom', mapping, key='DefaultDetector')
    custom_path = Path(custom_wrapper._get_resolved_file_path('model', mapping['model'])).name

    assert mirror_first_path == 'detect-20241225.ckpt'
    assert custom_path == 'detect-20241225.ckpt'


def test_hash_failure_continues_to_next_candidate_url(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))
    monkeypatch.delenv(model_sources.MODEL_SOURCES_ENV_VAR, raising=False)

    custom_url = 'https://custom.example.com/model.bin'
    official_url = 'https://github.com/example/project/releases/download/v1/model.bin'
    mirror_url = 'https://www.modelscope.cn/models/example/project/resolve/master/model.bin'
    _write_config(
        default_path,
        strategy='custom',
        custom_urls={
            'DummyWrapper:model': [custom_url],
        },
    )

    good_bytes = b'good-model'
    bad_bytes = b'bad-model'
    mapping = {
        'model': {
            'url': [official_url, mirror_url],
            'hash': _sha256_bytes(good_bytes),
            'file': 'model.bin',
        }
    }
    wrapper = _FileDownloadWrapper(
        tmp_path / 'models',
        mapping,
        key='DummyWrapper',
        temp_root=tmp_path / 'temp',
        url_to_bytes={
            custom_url: bad_bytes,
            official_url: good_bytes,
            mirror_url: good_bytes,
        },
    )

    asyncio.run(wrapper._download())

    final_path = tmp_path / 'models' / 'model.bin'
    assert wrapper.download_calls == [custom_url, official_url]
    assert final_path.read_bytes() == good_bytes
    assert not final_path.with_suffix('.bin.part').exists()




def test_archive_failure_continues_to_next_candidate_url(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))
    monkeypatch.delenv(model_sources.MODEL_SOURCES_ENV_VAR, raising=False)

    official_url = 'https://github.com/example/project/releases/download/v1/archive.zip'
    mirror_url = 'https://www.modelscope.cn/models/example/project/resolve/master/archive.zip'
    _write_config(default_path, strategy='official_first')

    mapping = {
        'model': {
            'url': [official_url, mirror_url],
            'archive': {
                'payload/model.txt': 'out/model.txt',
            },
        }
    }
    wrapper = _ArchiveDownloadWrapper(
        tmp_path / 'models',
        mapping,
        key='ArchiveWrapper',
        temp_root=tmp_path / 'temp',
        failing_urls={official_url},
        archive_relpath='payload/model.txt',
    )

    asyncio.run(wrapper._download())

    extracted_file = tmp_path / 'models' / 'out' / 'model.txt'
    assert wrapper.download_calls == [official_url, mirror_url]
    assert extracted_file.read_text(encoding='utf-8') == 'archive-ok'
    assert not (tmp_path / 'temp' / 'model' / 'archive.zip').exists()
    assert not (tmp_path / 'temp' / 'model' / 'extracted-0').exists()
    assert not (tmp_path / 'temp' / 'model' / 'extracted-1').exists()


def test_builtin_reference_sections_are_ignored_by_runtime_loader(tmp_path, monkeypatch):
    default_path = tmp_path / 'examples' / 'model_sources.toml'
    monkeypatch.setattr(model_sources, 'get_default_model_sources_path', lambda: str(default_path))
    monkeypatch.delenv(model_sources.MODEL_SOURCES_ENV_VAR, raising=False)

    _write_text(
        default_path,
        '\n'.join([
            'version = 1',
            'strategy = "custom"',
            '',
            '[builtin.official]',
            '"DummyWrapper:model" = ["https://readonly.example.com/official.bin"]',
            '',
            '[builtin.mirror]',
            '"DummyWrapper:model" = ["https://readonly.example.com/mirror.bin"]',
            '',
            '[custom.urls]',
            '"DummyWrapper:model" = ["https://custom.example.com/model.bin"]',
            '',
        ]),
    )

    config = model_sources.load_model_sources_config()
    assert config.strategy == 'custom'
    assert config.custom_urls == {
        'DummyWrapper:model': ['https://custom.example.com/model.bin'],
    }
