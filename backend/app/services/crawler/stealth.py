"""Playwright stealth utilities: fingerprint randomization and delay."""

import asyncio
import random
from typing import Any

# Common desktop user agents
USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Common viewport sizes
VIEWPORTS: list[dict[str, int]] = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1366, "height": 768},
    {"width": 2560, "height": 1440},
]

# Timezones
TIMEZONES: list[str] = [
    "Asia/Shanghai",
    "Asia/Chongqing",
]

# Languages
LANGUAGES: list[str] = [
    "zh-CN",
    "zh",
]


async def apply_stealth(page: Any) -> None:
    """Apply stealth settings to a Playwright page to avoid detection.

    Randomizes user agent, viewport, language, and timezone.

    Args:
        page: A Playwright page object (or any object with matching interface for mocking).
    """
    ua = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)
    timezone = random.choice(TIMEZONES)
    locale = random.choice(LANGUAGES)

    await page.set_extra_http_headers({
        "User-Agent": ua,
        "Accept-Language": f"{locale},zh;q=0.9,en;q=0.8",
    })
    await page.set_viewport_size(viewport)

    # Inject JS to override navigator properties
    await page.add_init_script(f"""
        Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
        Object.defineProperty(navigator, 'languages', {{get: () => ['{locale}', 'zh', 'en']}});
        Intl.DateTimeFormat.prototype.resolvedOptions = function() {{
            return {{timeZone: '{timezone}', locale: '{locale}'}};
        }};
    """)


async def random_delay(min_s: float = 5, max_s: float = 15) -> float:
    """Sleep for a random interval between min_s and max_s seconds.

    Args:
        min_s: Minimum seconds to sleep.
        max_s: Maximum seconds to sleep.

    Returns:
        The actual delay in seconds.
    """
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)
    return delay
