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
    "MANDATORY MAIN CHARACTER: A lovable cute muscular gorilla mascot. "
    "Huge round sparkly eyes, big warm friendly smile, chubby cartoon face. "
    "Pixar/Disney 3D clay animation style, soft rounded shapes, bright vivid colors. "
    "The gorilla MUST be the central subject filling most of the frame. "
    "Clean simple background. "
    "ABSOLUTE RULE - ZERO TEXT: no text, no letters, no words, no numbers, no digits, "
    "no symbols, no watermarks, no signs, no captions, no labels, no writing of any kind "
    "anywhere in the entire image. Pure visual imagery only."
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
                    aspect_ratio="1:1",
                    negative_prompt=(
                        "text, letters, words, numbers, digits, watermark, writing, "
                        "sign, caption, label, human, person, realistic photo"
                    ),
                    safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    person_generation="DONT_ALLOW",
                ),
            )
            response = future.result(timeout=IMAGE_TIMEOUT)
        if response.generated_images:
            return response.generated_images[0].image.image_bytes
        return None

    def generate_dynamic_situation(self, title: str, excerpt: str) -> str:
        """記事のタイトルと本文要約からゴリラのシチュエーションを動的に生成"""
        try:
            prompt_for_situation = f"""
You are a creative director for a gorilla mascot character.
Based on this article's title and content, describe a single, specific scene where the gorilla is acting out something related to the article's topic.
The description should be vivid, fun, and energetic. Include the gorilla's pose or action clearly.

Article Title: {title}
Content Summary: {excerpt}

Generate a 1-sentence description of what the gorilla is doing in the scene. Make it specific and action-oriented.
Example: "The gorilla is enthusiastically typing code on a laptop, eyes focused on the screen, one fist raised in triumph"
Example: "The gorilla is holding a smartphone up to its ear, grinning widely while gesturing excitedly"
Example: "The gorilla is wearing headphones and dancing joyfully while musical notes float around"

Output ONLY the 1-sentence scene description, nothing else.
"""
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt_for_situation,
                config=types.GenerateContentConfig(max_output_tokens=100),
            )
            situation = response.text.strip() if response else ""
            return situation if situation else "celebrating with joy and energy"
        except Exception as e:
            logger.warning(f"[IMAGE] Dynamic situation generation failed: {e}")
            return "celebrating with joy and energy"

    def build_prompt(self, keyword: str, description: str, title: str = "", excerpt: str = "") -> str:
        """記事テーマに合わせたゴリラシーンのプロンプトを生成する。"""
        # タイトルと本文がある場合は動的シチュエーションを生成
        if title and excerpt:
            situation = self.generate_dynamic_situation(title, excerpt)
        else:
            situation = description
        
        return (
            f"{GORILLA_BASE} "
            f"Scene: the gorilla mascot character is {situation}. "
            "The gorilla is always the hero of the scene, front and center. "
            "CRITICAL: Absolutely no text, no letters, no numbers, no writing, no watermarks anywhere. "
            "Pure visual imagery only."
        )
