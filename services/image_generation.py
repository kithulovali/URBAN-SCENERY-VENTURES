"""Image generation through the configured Google Gen AI image model."""
from __future__ import annotations

import base64
import os
from typing import Any


def generate_image(prompt: str) -> dict[str, Any]:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Image generation is unavailable: configure GOOGLE_API_KEY or GEMINI_API_KEY.")
    if not prompt.strip():
        raise ValueError("Image prompt must not be empty.")

    try:
        from google import genai
        from google.genai import types

        timeout_seconds = max(1, int(os.getenv("GEMINI_TIMEOUT_SECONDS", "60")))
        model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_seconds * 1000),
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=os.getenv("GEMINI_IMAGE_ASPECT_RATIO", "1:1")
                ),
            ),
        )
        for part in response.parts or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is not None and inline_data.data:
                raw = inline_data.data
                if isinstance(raw, str):
                    encoded = raw
                else:
                    encoded = base64.b64encode(raw).decode("ascii")
                return {
                    "model": model,
                    "mime_type": getattr(inline_data, "mime_type", None) or "image/png",
                    "image_base64": encoded,
                }
        raise RuntimeError("Image provider returned no image content.")
    except ValueError:
        raise
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Image generation request failed")
        raise RuntimeError(
            "Image generation failed; verify model availability, API access, and billing."
        ) from exc
