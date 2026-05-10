import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# マスコット画像のパス（assets/gorilla-mascot.png）
MASCOT_PATH = Path(__file__).parent / "assets" / "gorilla-mascot.png"


class ImageGenerator:
    def __init__(self):
        pass

    def generate(self, prompt: str = "") -> Optional[bytes]:
        """マスコット画像（gorilla-mascot.png）を返す。ファイルがなければ None。"""
        if MASCOT_PATH.exists():
            data = MASCOT_PATH.read_bytes()
            logger.info(f"[IMAGE] Using mascot: {MASCOT_PATH.name} ({len(data):,} bytes)")
            return data
        logger.warning(f"[IMAGE] Mascot not found: {MASCOT_PATH}")
        return None

    @staticmethod
    def build_prompt(keyword: str, description: str) -> str:
        return ""  # マスコット固定のため未使用
