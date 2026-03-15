"""Application configuration."""

BASE_URL = "https://centralnovel.com/series/lord-of-mysteries-20240505/"
AJAX_URL = "https://centralnovel.com/wp-admin/admin-ajax.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://centralnovel.com/",
}

DELAY_ENTRE_DOWNLOADS = 3
MAX_RETRIES = 3

QUALIDADE_JPG = 95
DPI = 150

LINKS_CSV = "links_capitulos.csv"

