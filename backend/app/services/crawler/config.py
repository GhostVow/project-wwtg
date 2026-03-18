"""Crawler-specific configuration: cities, keywords, rate limits."""

# Target cities
CITIES: list[str] = ["苏州", "上海", "杭州"]

# Search keywords per city (same set applied to each city)
SEARCH_KEYWORDS: list[str] = [
    "周末去哪玩",
    "周末一日游",
    "周末好去处",
    "亲子周末",
    "情侣周末约会",
    "周末遛娃",
    "周末散步",
    "周末野餐",
]

# Rate limiting
MAX_REQUESTS_PER_CITY: int = 200
REQUEST_INTERVAL: tuple[int, int] = (5, 15)  # min/max seconds between requests
BATCH_COOLDOWN: int = 60  # seconds between keyword batches

# Cookie TTL in Redis (seconds)
COOKIE_TTL: int = 86400  # 24 hours

# XHS base URL
XHS_SEARCH_URL: str = "https://www.xiaohongshu.com/search_result"
XHS_NOTE_URL: str = "https://www.xiaohongshu.com/explore/{note_id}"
