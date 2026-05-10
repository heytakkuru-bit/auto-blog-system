import base64
import logging
import os
import concurrent.futures
from typing import Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

IMAGE_MODELS = [
    os.getenv("IMAGEN_MODEL", "gemini-2.5-flash-image"),
    "imagen-4.0-fast-generate-001",
    "imagen-4.0-generate-001",
]
IMAGE_TIMEOUT = 60

# キャラクター定義（全プロンプト共通）
GORILLA_BASE = (
    "A cute muscular gorilla character with big round sparkling eyes and a warm smile. "
    "Pixar/Disney 3D clay animation style, soft rounded shapes, vibrant colors. "
    "Simple clean background. Square composition. "
    "IMPORTANT: absolutely no text, no letters, no numbers, no characters, "
    "no symbols, no watermarks, no signs, no writing of any kind anywhere in the image."
)


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
        candidates = response.candidates if response else []
        if not candidates or not candidates[0].content:
            return None
        for part in candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                data = part.inline_data.data
                if isinstance(data, str):
                    return base64.b64decode(data)
                return data
        return None

    def _generate_imagen(self, model: str, prompt: str) -> Optional[bytes]:
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
        """記事テーマに合わせたゴリラシーンのプロンプトを生成する。"""
        # keyword を英語寄りのシーン説明に変換（日本語キーワードがそのまま画像に出ないよう除外）
        return (
            f"{GORILLA_BASE} "
            f"Scene: the gorilla is enthusiastically and happily doing an activity "
            f"related to the topic: {description} "
            "Fun tech-savvy pose. No Japanese, no Chinese, no Korean, no text of any kind."
        )
