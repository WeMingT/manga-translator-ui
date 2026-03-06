from typing import Optional

import cv2
import numpy as np

from .common import CommonInpainter, OfflineInpainter
from .inpainting_aot import AotInpainter
from .inpainting_lama_mpe import LamaMPEInpainter, LamaLargeInpainter
from .none import NoneInpainter
from .original import OriginalInpainter
from ..config import Inpainter, InpainterConfig
from ..utils import (
    build_det_rearrange_plan,
    det_collect_plan_patches,
    det_rearrange_patch_array,
    det_unrearrange_patch_maps,
)

_SD_IMPORT_ERROR = None
try:
    from .inpainting_sd import StableDiffusionInpainter
except Exception as e:
    _SD_IMPORT_ERROR = e

    class StableDiffusionInpainter(OfflineInpainter):
        async def _load(self, device: str):
            raise RuntimeError(
                "Stable Diffusion inpainter is unavailable because optional dependencies are missing. "
                f"Original import error: {e!r}"
            )

        async def _infer(self, image: np.ndarray, mask: np.ndarray, inpainting_size: int = 1024, verbose: bool = False) -> np.ndarray:
            raise RuntimeError(
                "Stable Diffusion inpainter is unavailable because optional dependencies are missing. "
                f"Original import error: {e!r}"
            )

INPAINTERS = {
    Inpainter.default: AotInpainter,
    Inpainter.lama_large: LamaLargeInpainter,
    Inpainter.lama_mpe: LamaMPEInpainter,
    Inpainter.sd: StableDiffusionInpainter,
    Inpainter.none: NoneInpainter,
    Inpainter.original: OriginalInpainter,
}
inpainter_cache = {}

def get_inpainter(key: Inpainter, *args, **kwargs) -> CommonInpainter:
    if key not in INPAINTERS:
        raise ValueError(f'Could not find inpainter for: "{key}". Choose from the following: %s' % ','.join(INPAINTERS))
    if not inpainter_cache.get(key):
        inpainter = INPAINTERS[key]
        inpainter_cache[key] = inpainter(*args, **kwargs)
    return inpainter_cache[key]

async def prepare(inpainter_key: Inpainter, device: str = 'cpu', force_torch: bool = False):
    inpainter = get_inpainter(inpainter_key)
    if isinstance(inpainter, OfflineInpainter):
        await inpainter.download()
        await inpainter.load(device, force_torch=force_torch)


def _normalize_binary_mask(mask: np.ndarray) -> np.ndarray:
    if mask is None:
        return None
    mask_np = np.asarray(mask)
    if mask_np.ndim == 3:
        mask_np = mask_np[:, :, 0]
    return np.where(mask_np > 0, 255, 0).astype(np.uint8)


def _inpaint_handle_alpha_channel(original_alpha: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Keep RGBA alpha stable around inpainted areas based on surrounding alpha.
    """
    alpha_2d = original_alpha[:, :, 0] if original_alpha.ndim == 3 else original_alpha
    result_alpha = alpha_2d.copy()
    mask_bin = (_normalize_binary_mask(mask) > 0).astype(np.uint8)

    if not np.any(mask_bin > 0):
        return result_alpha

    mask_dilated = cv2.dilate(mask_bin, np.ones((15, 15), np.uint8), iterations=1)
    surrounding_mask = mask_dilated - mask_bin

    if np.any(surrounding_mask > 0):
        surrounding_alpha = result_alpha[surrounding_mask > 0]
        if surrounding_alpha.size > 0:
            median_surrounding_alpha = np.median(surrounding_alpha)
            if median_surrounding_alpha < 128:
                result_alpha[mask_bin > 0] = np.uint8(np.clip(np.rint(median_surrounding_alpha), 0, 255))

    return result_alpha

async def dispatch(inpainter_key: Inpainter, image: np.ndarray, mask: np.ndarray, config: Optional[InpainterConfig], inpainting_size: int = 1024, device: str = 'cpu', verbose: bool = False) -> np.ndarray:
    inpainter = get_inpainter(inpainter_key)
    config = config or InpainterConfig()
    if isinstance(inpainter, OfflineInpainter):
        force_torch = getattr(config, 'force_use_torch_inpainting', False)
        await inpainter.load(device, force_torch=force_torch)

    mask_binary = _normalize_binary_mask(mask)

    original_alpha = None
    image_rgb = image
    if image.ndim == 3 and image.shape[2] == 4:
        image_rgb = image[:, :, :3]
        original_alpha = image[:, :, 3]

    rearrange_plan = build_det_rearrange_plan(image_rgb, tgt_size=inpainting_size)
    if rearrange_plan is None:
        inpainted_rgb = await inpainter.inpaint(image_rgb, mask_binary, config, inpainting_size, verbose)
    else:
        inpainted_rgb = await _dispatch_with_det_rearrange(
            inpainter,
            image_rgb,
            mask_binary,
            config,
            inpainting_size,
            verbose,
            rearrange_plan,
        )

    if original_alpha is not None:
        alpha = _inpaint_handle_alpha_channel(original_alpha, mask_binary)
        return np.concatenate([inpainted_rgb, alpha[:, :, None]], axis=2)

    return inpainted_rgb

async def unload(inpainter_key: Inpainter):
    inpainter = inpainter_cache.pop(inpainter_key, None)
    if isinstance(inpainter, OfflineInpainter):
        await inpainter.unload()

async def _dispatch_with_det_rearrange(
    inpainter: CommonInpainter,
    image: np.ndarray,
    mask: np.ndarray,
    config: InpainterConfig,
    inpainting_size: int,
    verbose: bool,
    rearrange_plan: dict,
) -> np.ndarray:
    """
    使用与检测器统一的切割/回拼逻辑进行修复。
    """
    if verbose:
        h, w = image.shape[:2]
        print(
            f"[Inpainting Rearrange] image={w}x{h}, "
            f"patch_size={rearrange_plan['patch_size']}, "
            f"ph_num={rearrange_plan['ph_num']}, pw_num={rearrange_plan['pw_num']}, "
            f"pad_num={rearrange_plan['pad_num']}, transpose={rearrange_plan['transpose']}"
        )

    image_patch_array = det_rearrange_patch_array(rearrange_plan)
    mask_plan = dict(rearrange_plan)
    mask_plan['patch_list'] = det_collect_plan_patches(mask, rearrange_plan)
    mask_patch_array = det_rearrange_patch_array(mask_plan)

    inpainted_patch_list = []
    for ii, (image_patch, mask_patch) in enumerate(zip(image_patch_array, mask_patch_array)):
        mask_patch_binary = _normalize_binary_mask(mask_patch)
        if image_patch.size == 0:
            inpainted_patch_list.append(image_patch.astype(np.float32))
            continue
        if np.max(mask_patch_binary) == 0:
            inpainted_patch_list.append(image_patch.astype(np.float32))
            continue
        if verbose:
            print(f"[Inpainting Rearrange] processing patch {ii + 1}/{len(image_patch_array)}")
        inpainted_patch = await inpainter.inpaint(
            image_patch,
            mask_patch_binary,
            config,
            inpainting_size,
            verbose,
        )
        inpainted_patch_list.append(inpainted_patch.astype(np.float32))

    merged = det_unrearrange_patch_maps(inpainted_patch_list, rearrange_plan, data_format='hwc')
    merged = np.clip(np.rint(merged), 0, 255).astype(np.uint8)
    if verbose:
        print("[Inpainting Rearrange] patches merged successfully")
    return merged
