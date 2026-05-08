import os
import logging
import concurrent.futures
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-3.0-generate-008")
IMAGE_TIMEOUT = 60


class ImageGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> bytes | None:
        """画像を生成してbytesを返す。失敗時はNone。"""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(
                    self.client.models.generate_images,
                    model=IMAGEN_MODEL,
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
        except Exception as e:
            logger.warning(f"[IMAGE] Generation failed ({type(e).__name__}): {e}")
        return None

    @staticmethod
    def build_prompt(keyword: str, description: str) -> str:
        return (
            f"Professional illustration for Japanese tech blog article about '{keyword}'. "
            f"{description} "
            "Clean flat design style, modern and professional, bright colors, "
            "no text or letters in image, no watermarks, suitable for web article header."
        )
