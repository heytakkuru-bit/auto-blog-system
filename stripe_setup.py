"""
Stripe Payment Link 自動生成スクリプト
- 300円の固定商品を作成
- Payment Link を生成（決済後 THANKS_PAGE_URL へリダイレクト）
- 生成した URL を .env の STRIPE_PAYMENT_URL に自動書き込み

使い方:
  1. .env に STRIPE_SECRET_KEY=sk_live_... を追記
  2. python3 stripe_setup.py
"""
import os
import re
import sys
import logging
from pathlib import Path

import stripe
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PRICE_JPY = int(os.getenv("PRODUCT_PRICE", "300"))
THANKS_URL = os.getenv("THANKS_PAGE_URL", "https://teqsnap.com/thanks-95bb6f0c3e9c9ad2/")
PRODUCT_NAME = os.getenv("PRODUCT_NAME", "AIプロンプト集（実戦テンプレ3選）")


def create_payment_link() -> str:
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        logger.error(".env に STRIPE_SECRET_KEY が設定されていません")
        sys.exit(1)

    # 商品作成（既存があれば再利用）
    products = stripe.Product.list(limit=20, active=True)
    product = next((p for p in products.auto_paging_iter() if p.name == PRODUCT_NAME), None)
    if product:
        logger.info(f"既存の商品を再利用: {product.id}")
    else:
        product = stripe.Product.create(
            name=PRODUCT_NAME,
            description="AIプロンプト集 — コピペで即使える実戦テンプレート3選（2026年動作確認済み）",
        )
        logger.info(f"商品を作成: {product.id}")

    # 価格作成
    prices = stripe.Price.list(product=product.id, active=True, limit=5)
    price = next(
        (p for p in prices.auto_paging_iter() if p.unit_amount == PRICE_JPY),
        None,
    )
    if price:
        logger.info(f"既存の価格を再利用: {price.id} ({PRICE_JPY}円)")
    else:
        price = stripe.Price.create(
            product=product.id,
            unit_amount=PRICE_JPY,
            currency="jpy",
        )
        logger.info(f"価格を作成: {price.id} ({PRICE_JPY}円)")

    # Payment Link 作成
    payment_link = stripe.PaymentLink.create(
        line_items=[{"price": price.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {"url": THANKS_URL},
        },
        metadata={"product": PRODUCT_NAME},
    )
    url = payment_link.url
    logger.info(f"Payment Link 生成完了: {url}")
    return url


def update_env(payment_url: str) -> None:
    env_path = Path(__file__).parent / ".env"
    content = env_path.read_text(encoding="utf-8")

    if "STRIPE_PAYMENT_URL=" in content:
        content = re.sub(r"STRIPE_PAYMENT_URL=.*", f"STRIPE_PAYMENT_URL={payment_url}", content)
    else:
        content += f"\nSTRIPE_PAYMENT_URL={payment_url}\n"

    env_path.write_text(content, encoding="utf-8")
    logger.info(f".env を更新しました: STRIPE_PAYMENT_URL={payment_url}")


if __name__ == "__main__":
    url = create_payment_link()
    update_env(url)
    print(f"\n✅ 完了！決済リンク: {url}")
    print(f"   サンクスページ: {THANKS_URL}")
    print(f"\n次のコマンドで記事に反映できます:")
    print(f"  python3 repost_last3.py 3")
