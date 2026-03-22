import filecmp
import os
import re
import shutil
import stat
import sys
import tempfile
from abc import ABC, abstractmethod
from functools import cached_property

import torch

from ..config import TranslatorConfig
from ..model_sources import resolve_candidate_urls
from .generic import (
    BASE_PATH,
    download_url_with_progressbar,
    get_digest,
    get_filename_from_url,
    prompt_yes_no,
    replace_prefix,
)
from .log import get_logger


class InfererModule(ABC):
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        super().__init__()

    def parse_args(self, args: TranslatorConfig):
        """May be overwritten by super classes to parse commandline arguments"""
        pass

# class InfererModuleManager(ABC):
#     _KEY = ''
#     _VARIANTS = []

#     def __init__(self):
#         self.onstart: Callable = None
#         self.onfinish: Callable = None

#     def validate(self):
#         """
#         Throws exception if a
#         """
#         ...

#     async def prepare(self):
#         ...

#     async def dispatch(self):
#         ...


class ModelVerificationException(Exception):
    pass

class InvalidModelMappingException(ValueError):
    def __init__(self, cls: str, map_key: str, error_msg: str):
        error = f'[{cls}->{map_key}] Invalid _MODEL_MAPPING - {error_msg}'
        super().__init__(error)

class ModelWrapper(ABC):
    r"""
    A class that provides a unified interface for downloading models and making forward passes.
    All model inferer classes should extend it.

    Download specifications can be made through overwriting the `_MODEL_MAPPING` property.

    ```python
    _MODEL_MAPPTING = {
        'model_id': {
            **PARAMETERS
        },
        ...
    }
    ```

    Parameters:

    model_id            - Used for temporary caches and debug messages

        url                 - A direct download url

        hash                - Hash of downloaded file, Can be obtained upon ModelVerificationException

        file                - File download destination, If set to '.' the filename will be inferred
                              from the url (fallback is `model_id` value)

        archive             - Dict that contains all files/folders that are to be extracted from
                              the downloaded archive and their destinations, Mutually exclusive with `file`

        executables         - List of files that need to have the executable flag set
    """
    _MODEL_DIR = os.path.join(BASE_PATH, 'models')
    _MODEL_SUB_DIR = ''
    _MODEL_MAPPING = {}
    _KEY = ''

    def __init__(self):
        self.logger = getattr(self, 'logger', get_logger(self.__class__.__name__))
        os.makedirs(self.model_dir, exist_ok=True)
        self._key = self._KEY or self.__class__.__name__
        self._loaded = False
        self._check_for_malformed_model_mapping()
        self._downloaded = self._check_downloaded()

    def is_loaded(self) -> bool:
        return self._loaded

    def is_downloaded(self) -> bool:
        return self._downloaded

    @property
    def model_dir(self):
        return os.path.join(self._MODEL_DIR, self._MODEL_SUB_DIR)

    def _get_file_path(self, *args) -> str:
        return os.path.join(self.model_dir, *args)

    def _get_used_gpu_memory(self) -> bool:
        '''
        Gets the total amount of GPU memory used by model (Can be used in the future
        to determine whether a model should be loaded into vram or ram or automatically choose a model size).
        TODO: Use together with `--use-cuda-limited` flag to enforce stricter memory checks
        '''
        return torch.cuda.mem_get_info()

    def _get_builtin_urls(self, mapping) -> list[str]:
        raw_urls = mapping['url']
        return raw_urls if isinstance(raw_urls, list) else [raw_urls]

    def _get_model_source_id(self, map_key: str) -> str:
        return f'{self._key}:{map_key}'

    def _get_candidate_urls(self, map_key: str, mapping) -> list[str]:
        try:
            candidate_urls = resolve_candidate_urls(
                self._get_model_source_id(map_key),
                self._get_builtin_urls(mapping),
                logger=self.logger,
            )
        except Exception as exc:
            raise InvalidModelMappingException(self._key, map_key, f'Failed to resolve candidate urls: {exc}') from exc

        if not candidate_urls:
            raise InvalidModelMappingException(self._key, map_key, 'No candidate urls available')
        return candidate_urls

    def _get_stable_filename(self, map_key: str, mapping) -> str:
        for url in self._get_builtin_urls(mapping):
            filename = get_filename_from_url(url, '')
            if filename:
                return filename
        return map_key

    def _get_resolved_file_relpath(self, map_key: str, mapping) -> str:
        path = mapping['file']
        if os.path.basename(path) in ('', '.'):
            path = os.path.join(path, self._get_stable_filename(map_key, mapping))
        return path

    def _get_resolved_file_path(self, map_key: str, mapping) -> str:
        return self._get_file_path(self._get_resolved_file_relpath(map_key, mapping))

    def _get_temp_map_directory(self, map_key: str) -> str:
        p = os.path.join(self._temp_working_directory, map_key)
        os.makedirs(p, exist_ok=True)
        return p

    def _get_archive_download_path(self, map_key: str, mapping, url: str) -> str:
        filename = get_filename_from_url(url, self._get_stable_filename(map_key, mapping))
        return os.path.join(self._get_temp_map_directory(map_key), filename)

    def _get_archive_extract_path(self, map_key: str, candidate_index: int) -> str:
        return os.path.join(self._get_temp_map_directory(map_key), f'extracted-{candidate_index}')

    def _remove_path(self, path: str):
        if os.path.islink(path) or os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)

    def _cleanup_paths(self, *paths: str):
        for path in paths:
            if not path or not os.path.exists(path):
                continue
            try:
                self._remove_path(path)
            except Exception:
                pass

    def _resolve_archive_destination_path(self, orig: str, dest: str) -> str:
        p = self._get_file_path(dest)
        if os.path.basename(p) in ('', '.'):
            archive_name = os.path.basename(orig[:-1] if orig.endswith('/') else orig)
            p = os.path.join(p, archive_name)
        return p

    def _check_for_malformed_model_mapping(self):
        for map_key, mapping in self._MODEL_MAPPING.items():
            if 'url' not in mapping:
                raise InvalidModelMappingException(self._key, map_key, 'Missing url property')

            urls = self._get_builtin_urls(mapping)
            if len(urls) == 0:
                raise InvalidModelMappingException(self._key, map_key, 'Empty url property')
            for url in urls:
                if not re.search(r'^https?://', url):
                    raise InvalidModelMappingException(self._key, map_key, 'Malformed url property: "%s"' % url)

            if 'file' not in mapping and 'archive' not in mapping:
                mapping['file'] = '.'
            elif 'file' in mapping and 'archive' in mapping:
                raise InvalidModelMappingException(self._key, map_key, 'Properties file and archive are mutually exclusive')

            if 'archive' in mapping and not isinstance(mapping['archive'], dict):
                raise InvalidModelMappingException(self._key, map_key, 'Property archive must be a dict')

    async def _download_file(self, url: str, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f' -- Downloading: "{url}"')
        download_url_with_progressbar(url, path)

    async def _verify_file(self, sha256_pre_calculated: str, path: str):
        print(f' -- Verifying: "{path}"')
        sha256_calculated = get_digest(path).lower()
        sha256_pre_calculated = sha256_pre_calculated.lower()

        if sha256_calculated != sha256_pre_calculated:
            self._on_verify_failure(sha256_calculated, sha256_pre_calculated)
        else:
            print(' -- Verifying: OK!')

    def _on_verify_failure(self, sha256_calculated: str, sha256_pre_calculated: str):
        print(f' -- Mismatch between downloaded and created hash: "{sha256_calculated}" <-> "{sha256_pre_calculated}"')
        raise ModelVerificationException()

    @cached_property
    def _temp_working_directory(self):
        p = os.path.join(tempfile.gettempdir(), 'manga-image-translator', self._key.lower())
        os.makedirs(p, exist_ok=True)
        return p

    async def download(self, force=False):
        '''
        Downloads required models.
        '''
        if force or not self.is_downloaded():
            while True:
                try:
                    await self._download()
                    self._downloaded = True
                    break
                except ModelVerificationException:
                    if not prompt_yes_no('Failed to verify signature. Do you want to restart the download?', default=True):
                        print('Aborting.', end='')
                        raise KeyboardInterrupt()

    def _extract_archive(self, download_path: str, extracted_path: str):
        print(' -- Extracting files')
        if download_path.endswith('.7z'):
            try:
                import py7zr
            except ImportError as exc:
                raise ImportError('py7zr is required for .7z archives. Install it with: pip install py7zr') from exc

            os.makedirs(extracted_path, exist_ok=True)
            with py7zr.SevenZipFile(download_path, mode='r') as archive:
                archive.extractall(path=extracted_path)
        else:
            shutil.unpack_archive(download_path, extracted_path)

    def _get_real_archive_files(self, extracted_path: str) -> list[str]:
        archive_files = []
        for root, dirs, files in os.walk(extracted_path):
            for name in files:
                file_path = replace_prefix(os.path.join(root, name), extracted_path, '')
                archive_files.append(file_path)
        return archive_files

    def _move_archive_files(self, map_key: str, mapping, extracted_path: str) -> list[str]:
        moved_paths: list[str] = []

        if len(mapping['archive']) == 0:
            raise InvalidModelMappingException(
                self._key,
                map_key,
                'No archive files specified\nAvailable files:\n%s' % '\n'.join(self._get_real_archive_files(extracted_path)),
            )

        for orig, dest in mapping['archive'].items():
            src_path = os.path.join(extracted_path, orig)
            if not os.path.exists(src_path):
                raise InvalidModelMappingException(
                    self._key,
                    map_key,
                    f'File "{orig}" does not exist within archive\nAvailable files:\n%s' % '\n'.join(self._get_real_archive_files(extracted_path)),
                )

            dest_path = self._resolve_archive_destination_path(orig, dest)
            if os.path.exists(dest_path):
                if os.path.isfile(src_path) and os.path.isfile(dest_path) and filecmp.cmp(src_path, dest_path, shallow=False):
                    continue
                raise InvalidModelMappingException(self._key, map_key, f'File "{orig}" already exists at "{dest}"')

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.move(src_path, dest_path)
            moved_paths.append(dest_path)

        return moved_paths

    async def _download_file_candidate(self, map_key: str, mapping, url: str):
        final_path = self._get_resolved_file_path(map_key, mapping)
        part_path = final_path + '.part'
        final_existed_before = os.path.exists(final_path)

        try:
            await self._download_file(url, part_path)
            if 'hash' in mapping:
                await self._verify_file(mapping['hash'], part_path)
            if os.path.exists(final_path):
                os.remove(final_path)
            os.replace(part_path, final_path)
        except Exception:
            cleanup_paths = [part_path]
            if not final_existed_before:
                cleanup_paths.append(final_path)
            self._cleanup_paths(*cleanup_paths)
            raise

    async def _download_archive_candidate(self, map_key: str, mapping, url: str, candidate_index: int):
        download_path = self._get_archive_download_path(map_key, mapping, url)
        extracted_path = self._get_archive_extract_path(map_key, candidate_index)
        moved_paths: list[str] = []

        try:
            self._cleanup_paths(download_path, extracted_path)
            await self._download_file(url, download_path)
            if 'hash' in mapping:
                await self._verify_file(mapping['hash'], download_path)
            self._extract_archive(download_path, extracted_path)
            moved_paths = self._move_archive_files(map_key, mapping, extracted_path)
        except Exception:
            self._cleanup_paths(*reversed(moved_paths))
            self._cleanup_paths(download_path, extracted_path)
            raise
        else:
            self._cleanup_paths(download_path, extracted_path)

    async def _download_mapping(self, map_key: str, mapping):
        candidate_urls = self._get_candidate_urls(map_key, mapping)

        for i, current_url in enumerate(candidate_urls):
            try:
                if i > 0:
                    print(f' -- Trying fallback URL {i}: "{current_url}"')
                if 'archive' in mapping:
                    await self._download_archive_candidate(map_key, mapping, current_url, i)
                else:
                    await self._download_file_candidate(map_key, mapping, current_url)
                self._grant_execute_permissions(map_key)
                return
            except Exception as e:
                if i < len(candidate_urls) - 1:
                    print(f' -- Candidate failed: {e}')
                    print(' -- Switching to fallback URL...')
                else:
                    raise

    async def _download(self):
        '''
        Downloads models as defined in `_MODEL_MAPPING`. Can be overwritten (together
        with `_check_downloaded`) to implement unconventional download logic.
        '''
        print(f'\nDownloading models into {self.model_dir}\n')
        for map_key, mapping in self._MODEL_MAPPING.items():
            if self._check_downloaded_map(map_key):
                print(f' -- Skipping {map_key} as it\'s already downloaded')
                continue

            await self._download_mapping(map_key, mapping)
            print()
            self._on_download_finished(map_key)

    def _on_download_finished(self, map_key):
        '''
        Can be overwritten to further process the downloaded files
        '''
        pass

    def _check_downloaded(self) -> bool:
        '''
        Scans filesystem for required files as defined in `_MODEL_MAPPING`.
        Returns `False` if files should be redownloaded.
        '''
        for map_key in self._MODEL_MAPPING:
            if not self._check_downloaded_map(map_key):
                return False
        return True

    def _check_downloaded_map(self, map_key: str) -> bool:
        """Check if model file exists

        Args:
            map_key (str): key in self._MODEL_MAPPING

        Returns:
            bool: the "file" or "archive" file exists
        """
        mapping = self._MODEL_MAPPING[map_key]

        if 'file' in mapping:
            if not os.path.exists(self._get_resolved_file_path(map_key, mapping)):
                return False

        elif 'archive' in mapping:
            for orig, dest in mapping['archive'].items():
                if not os.path.exists(self._resolve_archive_destination_path(orig, dest)):
                    return False

        self._grant_execute_permissions(map_key)

        return True

    def _grant_execute_permissions(self, map_key: str):
        mapping = self._MODEL_MAPPING[map_key]

        if sys.platform == 'linux':
            # Grant permission to executables
            for file in mapping.get('executables', []):
                p = self._get_file_path(file)
                if os.path.basename(p) in ('', '.'):
                    p = os.path.join(p, file)
                if not os.path.isfile(p):
                    raise InvalidModelMappingException(self._key, map_key, f'File "{file}" does not exist')
                if not os.access(p, os.X_OK):
                    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    async def reload(self, device: str, **kwargs):
        await self.unload()
        await self.load(device=device, **kwargs)

    async def load(self, device: str, **kwargs):
        '''
        Loads models into memory. Has to be called before `forward`.
        '''
        if not self.is_downloaded():
            await self.download()
        if not self.is_loaded():
            await self._load(device=device, **kwargs)
            self._loaded = True

    async def unload(self):
        if self.is_loaded():
            await self._unload()
            self._loaded = False
            # 统一卸载后内存清理，确保检测/修复等模型直接卸载时也回收显存。
            try:
                import gc
                gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    if hasattr(torch.cuda, 'ipc_collect'):
                        torch.cuda.ipc_collect()
            except Exception:
                pass

    async def infer(self, *args, **kwargs):
        '''
        Makes a forward pass through the network.
        '''
        if not self.is_loaded():
            raise Exception(f'{self._key}: Tried to forward pass without having loaded the model.')

        return await self._infer(*args, **kwargs)

    @abstractmethod
    async def _load(self, device: str, *args, **kwargs):
        pass

    @abstractmethod
    async def _unload(self):
        pass

    @abstractmethod
    async def _infer(self, *args, **kwargs):
        pass
