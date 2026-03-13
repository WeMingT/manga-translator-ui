import base64
import io
import json
import re
from typing import Awaitable, Callable, Optional

from PIL import Image

from .retry import summarize_exception_message, summarize_response_text


_OPENAI_IMAGE_INTERFACE_CACHE: dict[tuple[str, str], str] = {}
_OPENAI_IMAGE_INTERFACES = ("images/edits", "images/generations", "chat/completions")
_ENDPOINT_FALLBACK_STATUS_CODES = {404, 405, 501}
_DATA_URL_RE = re.compile(r"data:image/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=_-]+")


async def request_openai_image_with_fallback(
    *,
    session,
    base_url: str,
    api_key: str,
    default_headers: Optional[dict],
    model_name: str,
    prompt_text: str,
    image_bytes: bytes,
    filename: str,
    timeout: float,
    fetch_remote_image: Callable[[str], Awaitable[Image.Image]],
    provider_name: str,
    logger,
    extra_images: Optional[list[dict]] = None,
    extra_request_params: Optional[dict] = None,
) -> Image.Image:
    from curl_cffi import CurlMime

    base_url = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"}
    if default_headers:
        headers.update(default_headers)

    extra_images = extra_images or []
    extra_request_params = _normalize_extra_request_params(extra_request_params)
    cache_key = (base_url, model_name)
    candidate_interfaces = _build_candidate_interfaces(
        cache_key=cache_key,
        has_extra_images=bool(extra_images),
    )

    errors: list[str] = []

    for index, interface_name in enumerate(candidate_interfaces):
        next_interface_name = candidate_interfaces[index + 1] if index + 1 < len(candidate_interfaces) else None
        if interface_name == "images/edits":
            if extra_images:
                errors.append("images/edits skipped because reference images require chat/completions")
                continue
            multipart = CurlMime()
            multipart.addpart(
                name="image",
                filename=filename,
                content_type="image/png",
                data=image_bytes,
            )
            try:
                request_data = {
                    "model": model_name,
                    "prompt": prompt_text,
                    "response_format": "b64_json",
                }
                if extra_request_params:
                    request_data.update(
                        {
                            key: json.dumps(value, ensure_ascii=False)
                            if isinstance(value, (dict, list))
                            else value
                            for key, value in extra_request_params.items()
                        }
                    )
                response = await session.post(
                    f"{base_url}/images/edits",
                    headers=headers,
                    data=request_data,
                    multipart=multipart,
                    timeout=timeout,
                )
            finally:
                multipart.close()

            if response.status_code == 200:
                try:
                    payload = response.json()
                except Exception as exc:
                    raise RuntimeError(
                        f"{provider_name} {base_url}/images/edits returned invalid JSON: "
                        f"{summarize_exception_message(exc)}"
                    ) from exc
                image = await _extract_image_from_images_payload(
                    payload=payload,
                    fetch_remote_image=fetch_remote_image,
                )
                if image is not None:
                    _OPENAI_IMAGE_INTERFACE_CACHE[cache_key] = interface_name
                    return image
                errors.append("images/edits returned 200 but did not contain image data")
                continue

            if _should_try_next_interface(response.status_code, response.text):
                _log_fallback(
                    logger=logger,
                    provider_name=provider_name,
                    endpoint=f"{base_url}/images/edits",
                    status_code=response.status_code,
                    next_interface_name=next_interface_name,
                )
                errors.append(f"images/edits HTTP {response.status_code}")
                continue

            raise RuntimeError(
                f"{provider_name} request failed at {base_url}/images/edits "
                f"with status {response.status_code}: "
                f"{_response_text_preview(response.text)}"
            )

        if interface_name == "images/generations":
            generation_images = [
                f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"
            ]
            generation_images.extend(
                f"data:image/png;base64,{base64.b64encode(item['image_bytes']).decode('ascii')}"
                for item in extra_images
                if isinstance(item.get("image_bytes"), (bytes, bytearray))
            )
            request_json = {
                "model": model_name,
                "prompt": prompt_text,
                "response_format": "b64_json",
            }
            request_json.update(extra_request_params)
            if generation_images:
                request_json.setdefault(
                    "image",
                    generation_images if len(generation_images) > 1 else generation_images[0],
                )
            if len(generation_images) > 1:
                request_json.setdefault("sequential_image_generation", "disabled")

            response = await session.post(
                f"{base_url}/images/generations",
                headers=headers,
                json=request_json,
                timeout=timeout,
            )

            if response.status_code == 200:
                try:
                    payload = response.json()
                except Exception as exc:
                    raise RuntimeError(
                        f"{provider_name} {base_url}/images/generations returned invalid JSON: "
                        f"{summarize_exception_message(exc)}"
                    ) from exc
                image = await _extract_image_from_images_payload(
                    payload=payload,
                    fetch_remote_image=fetch_remote_image,
                )
                if image is not None:
                    _OPENAI_IMAGE_INTERFACE_CACHE[cache_key] = interface_name
                    return image
                errors.append("images/generations returned 200 but did not contain image data")
                continue

            if _should_try_next_interface(
                response.status_code,
                response.text,
                interface_name=interface_name,
            ):
                _log_fallback(
                    logger=logger,
                    provider_name=provider_name,
                    endpoint=f"{base_url}/images/generations",
                    status_code=response.status_code,
                    next_interface_name=next_interface_name,
                )
                errors.append(f"images/generations HTTP {response.status_code}")
                continue

            raise RuntimeError(
                f"{provider_name} request failed at {base_url}/images/generations "
                f"with status {response.status_code}: "
                f"{_response_text_preview(response.text)}"
            )

        message_content = [
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"
                },
            },
        ]
        for idx, item in enumerate(extra_images, start=1):
            label = str(item.get("label") or f"Reference image {idx}")
            extra_image_bytes = item.get("image_bytes")
            if not isinstance(extra_image_bytes, (bytes, bytearray)):
                continue
            message_content.append({"type": "text", "text": f"Reference image {idx}: {label}"})
            message_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64.b64encode(extra_image_bytes).decode('ascii')}"
                    },
                }
            )

        request_json = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": message_content,
                }
            ],
        }
        if extra_request_params:
            request_json.update(extra_request_params)

        response = await session.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=request_json,
            timeout=timeout,
        )

        if response.status_code == 200:
            try:
                payload = response.json()
            except Exception as exc:
                raise RuntimeError(
                    f"{provider_name} {base_url}/chat/completions returned invalid JSON: "
                    f"{summarize_exception_message(exc)}"
                ) from exc
            image = await _extract_image_from_chat_payload(
                payload=payload,
                fetch_remote_image=fetch_remote_image,
            )
            if image is not None:
                _OPENAI_IMAGE_INTERFACE_CACHE[cache_key] = interface_name
                return image

            text_preview = _extract_text_preview(payload)
            message = "chat/completions returned 200 but did not contain an image"
            if text_preview:
                message = f"{message}; text preview: {summarize_response_text(text_preview)}"
            errors.append(message)
            continue

        if _should_try_next_interface(response.status_code, response.text):
            _log_fallback(
                logger=logger,
                provider_name=provider_name,
                endpoint=f"{base_url}/chat/completions",
                status_code=response.status_code,
                next_interface_name=next_interface_name,
            )
            errors.append(f"chat/completions HTTP {response.status_code}")
            continue

        raise RuntimeError(
            f"{provider_name} request failed at {base_url}/chat/completions "
            f"with status {response.status_code}: "
            f"{_response_text_preview(response.text)}"
        )

    attempts = ", ".join(errors) if errors else "no compatible image interface responded"
    raise RuntimeError(
        f"{provider_name} could not find a compatible image output interface under {base_url}. "
        f"Tried /images/edits, /images/generations, and /chat/completions. Details: {attempts}. "
        f"This API base may only support text chat and vision input, not image generation/editing output."
    )


def _build_candidate_interfaces(*, cache_key: tuple[str, str], has_extra_images: bool) -> list[str]:
    preferred_interface = _OPENAI_IMAGE_INTERFACE_CACHE.get(cache_key)
    if preferred_interface:
        default_order = [preferred_interface]
    elif has_extra_images:
        default_order = ["images/generations", "chat/completions", "images/edits"]
    else:
        default_order = ["images/edits", "images/generations", "chat/completions"]

    candidate_interfaces = list(default_order)
    candidate_interfaces.extend(
        interface for interface in _OPENAI_IMAGE_INTERFACES if interface not in candidate_interfaces
    )
    return candidate_interfaces


def _normalize_extra_request_params(extra_request_params: Optional[dict]) -> dict:
    normalized = dict(extra_request_params or {})
    extra_body = normalized.pop("extra_body", None)
    if isinstance(extra_body, dict):
        for key, value in extra_body.items():
            normalized.setdefault(key, value)
    return normalized


def _log_fallback(*, logger, provider_name: str, endpoint: str, status_code: int, next_interface_name: Optional[str]):
    if not next_interface_name:
        return
    logger.warning(
        f"{provider_name}: {endpoint} unavailable (HTTP {status_code}), "
        f"trying /{next_interface_name}."
    )


def _should_try_next_interface(status_code: int, response_text: str, interface_name: Optional[str] = None) -> bool:
    if status_code in _ENDPOINT_FALLBACK_STATUS_CODES:
        return True
    text = (response_text or "").lower()
    fallback_markers = (
        "not found",
        "unknown url",
        "unknown path",
        "unsupported endpoint",
        "unsupported route",
        "does not support",
    )
    if any(marker in text for marker in fallback_markers):
        return True

    if status_code in {400, 415, 422} and interface_name == "images/generations":
        generation_markers = (
            "unknown parameter",
            "unknown field",
            "unrecognized field",
            "extra fields not permitted",
            "additional properties are not allowed",
            "reference_images",
            "does not support image",
            "does not support reference image",
        )
        return any(marker in text for marker in generation_markers)

    return False


def _response_text_preview(text: str, limit: Optional[int] = None) -> str:
    return summarize_response_text(text, limit=limit)


async def _extract_image_from_images_payload(
    payload: dict,
    fetch_remote_image: Callable[[str], Awaitable[Image.Image]],
) -> Optional[Image.Image]:
    data = payload.get("data") or []
    for item in data:
        image = await _image_from_candidate(item, fetch_remote_image)
        if image is not None:
            return image
    return None


async def _extract_image_from_chat_payload(
    payload: dict,
    fetch_remote_image: Callable[[str], Awaitable[Image.Image]],
) -> Optional[Image.Image]:
    for candidate in (
        payload.get("image"),
        *(payload.get("images") or []),
    ):
        image = await _image_from_candidate(candidate, fetch_remote_image)
        if image is not None:
            return image

    choices = payload.get("choices") or []
    for choice in choices:
        message = choice.get("message") or {}
        for candidate in (
            message.get("image"),
            *(message.get("images") or []),
        ):
            image = await _image_from_candidate(candidate, fetch_remote_image)
            if image is not None:
                return image

        content = message.get("content")
        image = await _extract_image_from_content(content, fetch_remote_image)
        if image is not None:
            return image

    image = await _extract_image_from_images_payload(payload, fetch_remote_image)
    if image is not None:
        return image

    return await _extract_image_from_content(payload.get("output"), fetch_remote_image)


async def _extract_image_from_content(
    content,
    fetch_remote_image: Callable[[str], Awaitable[Image.Image]],
) -> Optional[Image.Image]:
    if isinstance(content, list):
        for item in content:
            image = await _image_from_candidate(item, fetch_remote_image)
            if image is not None:
                return image
    elif isinstance(content, dict):
        image = await _image_from_candidate(content, fetch_remote_image)
        if image is not None:
            return image
    elif isinstance(content, str):
        return await _image_from_candidate(content, fetch_remote_image)
    return None


async def _image_from_candidate(
    candidate,
    fetch_remote_image: Callable[[str], Awaitable[Image.Image]],
) -> Optional[Image.Image]:
    if isinstance(candidate, str):
        return await _image_from_string(candidate, fetch_remote_image)

    if not isinstance(candidate, dict):
        return None

    for key in ("text", "content"):
        value = candidate.get(key)
        if isinstance(value, str):
            image = await _image_from_string(value, fetch_remote_image)
            if image is not None:
                return image

    for key in ("b64_json", "image_base64", "b64"):
        value = candidate.get(key)
        if isinstance(value, str):
            image = _load_image_from_base64(value)
            if image is not None:
                return image

    inline_data = candidate.get("inlineData") or candidate.get("inline_data")
    if isinstance(inline_data, dict):
        data = inline_data.get("data")
        if isinstance(data, str):
            image = _load_image_from_base64(data)
            if image is not None:
                return image

    if isinstance(candidate.get("image_url"), dict):
        url = candidate["image_url"].get("url")
        if isinstance(url, str):
            return await _image_from_string(url, fetch_remote_image)

    for key in ("url", "image_url"):
        value = candidate.get(key)
        if isinstance(value, str):
            return await _image_from_string(value, fetch_remote_image)

    for nested_key in ("image", "content", "output", "result"):
        nested_value = candidate.get(nested_key)
        image = await _extract_image_from_content(nested_value, fetch_remote_image)
        if image is not None:
            return image

    return None


async def _image_from_string(
    value: str,
    fetch_remote_image: Callable[[str], Awaitable[Image.Image]],
) -> Optional[Image.Image]:
    image = _load_image_from_data_url(value)
    if image is not None:
        return image
    if value.startswith("http://") or value.startswith("https://"):
        return await fetch_remote_image(value)
    return None


def _load_image_from_data_url(value: str) -> Optional[Image.Image]:
    match = _DATA_URL_RE.search(value)
    if match is None:
        return None
    _, encoded = match.group(0).split(";base64,", 1)
    return _load_image_from_base64(encoded)


def _load_image_from_base64(value: str) -> Optional[Image.Image]:
    try:
        return Image.open(io.BytesIO(base64.b64decode(value))).convert("RGB")
    except Exception:
        return None


def _extract_text_preview(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts).strip()
    return ""
