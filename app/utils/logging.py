"""アプリ全体で利用するロガー設定。"""

import logging
import sys

from app.config.config import settings


def setup_logging() -> logging.Logger:
    """標準出力向けロガー設定を初期化して返す。

    Args:
        なし。

    Returns:
        名前空間 `aituber` のロガー。
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("aituber")


logger = setup_logging()
