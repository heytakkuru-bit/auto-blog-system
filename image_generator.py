import base64
import logging
import os
import concurrent.futures
from typing import Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# 利用可能な画像生成モデル（課金有効時）
# gemini-2.5-flash-image : generate_content + response_modalities=["IMAGE"]
# imagen-4.0-fast-generate-001 : generate_images (高速・低コスト)
# imagen-4.0-generate-001      : generate_images (高品質)
IMAGE_MODELS = [
    os.getenv("IMAGEN_MODEL", "gemini-2.5-flash-image"),
    "imagen-4.0-fast-generate-001",
    "imagen-4.0-generate-001",
]
IMAGE_TIMEOUT = 60


class ImageGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> Optional[bytes]:
        """画像を生成してbytesを返す。失敗時はNone。"""
        for model in IMAGE_MODELS:
            result = self._try_model(model, prompt)
            if result:
                logger.info(f"[IMAGE] Generated with {model}")
                return result
        logger.warning("[IMAGE] All image models failed")
        return None

    def _try_model(self, model: str, prompt: str) -> Optional[bytes]:
        try:
            if model.startswith("gemini-"):
                return self._generate_gemini(model, prompt)
            else:
                return self._generate_imagen(model, prompt)
        except Exception as e:
            logger.warning(f"[IMAGE] {model} failed ({type(e).__name__}): {e}")
            return None

    def _generate_gemini(self, model: str, prompt: str) -> Optional[bytes]:
        """gemini-* モデルで generate_content + response_modalities=IMAGE を使う。"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(
                self.client.models.generate_content,
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            response = future.result(timeout=IMAGE_TIMEOUT)
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                data = part.inline_data.data
                # SDK によって str(base64) か bytes かが異なる
                if isinstance(data, str):
                    return base64.b64decode(data)
                return data
        return None

    def _generate_imagen(self, model: str, prompt: str) -> Optional[bytes]:
        """imagen-* モデルで generate_images を使う。"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(
                self.client.models.generate_images,
                model=model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    person_generation="DONT_ALLOW",
                ),
            )
            response = future.result(timeout=IMAGE_TIMEOUT)
        if response.generated_images:
            return response.generated_images[0].image.image_bytes
        return None

    @staticmethod
    def build_prompt(keyword: str, description: str) -> str:
        return (
            f"Professional illustration for Japanese tech blog article about '{keyword}'. "
            f"{description} "
            "Clean flat design style, modern and professional, bright colors, "
            "no text or letters in image, no watermarks, suitable for web article header."
        )
