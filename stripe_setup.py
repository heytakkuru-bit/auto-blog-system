"""
Stripe Payment Link 自動生成スクリプト（松・竹 二段構え対応）

商品構成:
  竹（標準）: 300円  — 記事別プロンプト集
  松（高級）: 3,000円 — 個別相談 or フルセット（将来展開）

使い方:
  python3 stripe_setup.py take    # 竹（300円）のリンク生成
  python3 stripe_setup.py matsu   # 松（3,000円）のリンク生成
  python3 stripe_setup.py both    # 両方生成（デフォルト）

前提: .env に STRIPE_SECRET_KEY=sk_live_... を追記しておく
"""
import os, re, sys, logging
from pathlib import Path
import stripe
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

THANKS_URL = os.getenv("THANKS_PAGE_URL", "https://teqsnap.com/thanks-95bb6f0c3e9c9ad2/")

PLANS = {
    "take": {
        "name":        "【竹】AIプロンプト集（実戦テンプレ3選）",
        "description": "記事テーマ別の実戦プロンプト3選 — コピペで即使える・2026年動作確認済み",
        "price_jpy":   300,
        "env_key":     "STRIPE_PAYMENT_URL",          # 既存キーと互換
        "env_key_alt": "STRIPE_PAYMENT_URL_TAKE",
    },
    "matsu": {
        "name":        "【松】AIフル活用サポートセット",
        "description": "全記事プロンプト集 + 個別チャット相談1回 — AI完全初心者向け伴走プラン",
        "price_jpy":   3000,
        "env_key":     "STRIPE_PAYMENT_URL_MATSU",
        "env_key_alt": None,
    },
}


def get_or_create_product(name: str, description: str) -> str:
    products = stripe.Product.list(limit=50, active=True)
    for p in products.auto_paging_iter():
        if p.name == name:
            logger.info(f"既存商品を再利用: {p.id} ({name})")
            return p.id
    p = stripe.Product.create(name=name, description=description)
    logger.info(f"商品を作成: {p.id} ({name})")
    return p.id


def get_or_create_price(product_id: str, amount: int) -> str:
    prices = stripe.Price.list(product=product_id, active=True, limit=10)
    for p in prices.auto_paging_iter():
        if p.unit_amount == amount and p.currency == "jpy":
            logger.info(f"既存価格を再利用: {p.id} ({amount}円)")
            return p.id
    p = stripe.Price.create(product=product_id, unit_amount=amount, currency="jpy")
    logger.info(f"価格を作成: {p.id} ({amount}円)")
    return p.id


def create_payment_link(price_id: str, thanks_url: str) -> str:
    pl = stripe.PaymentLink.create(
        line_items=[{"price": price_id, "quantity": 1}],
        after_completion={"type": "redirect", "redirect": {"url": thanks_url}},
    )
    logger.info(f"Payment Link 生成: {pl.url}")
    return pl.url


def update_env(key: str, value: str) -> None:
    env_path = Path(__file__).parent / ".env"
    content = env_path.read_text(encoding="utf-8")
    if f"{key}=" in content:
        content = re.sub(rf"{key}=.*", f"{key}={value}", content)
    else:
        content += f"\n{key}={value}\n"
    env_path.write_text(content, encoding="utf-8")
    logger.info(f".env 更新: {key}={value}")


def run(tier: str) -> None:
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        logger.error(".env に STRIPE_SECRET_KEY が未設定です")
        sys.exit(1)

    plan = PLANS[tier]
    product_id = get_or_create_product(plan["name"], plan["description"])
    price_id   = get_or_create_price(product_id, plan["price_jpy"])
    url        = create_payment_link(price_id, THANKS_URL)

    update_env(plan["env_key"], url)
    if plan["env_key_alt"]:
        update_env(plan["env_key_alt"], url)

    print(f"\n✅ 【{tier}】{plan['price_jpy']}円 Payment Link: {url}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    if mode == "both":
        run("take")
        run("matsu")
    elif mode in PLANS:
        run(mode)
    else:
        print(f"使い方: python3 stripe_setup.py [take|matsu|both]")
        sys.exit(1)
    print(f"\nサンクスページ: {THANKS_URL}")
    print("次: python3 repost_last3.py 3")
