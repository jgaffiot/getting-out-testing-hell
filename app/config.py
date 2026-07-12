import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://bookstore:bookstore@localhost:5432/bookstore"
)

PAYMENT_API_URL = "https://api.fakepay.io/v1"
PAYMENT_API_KEY = os.environ.get("PAYMENT_API_KEY", "sk_test_changeme")

EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "localhost")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "1025"))
EMAIL_FROM = "shop@bookstore.local"

CANCELLATION_WINDOW_HOURS = 1
MAX_ITEMS_PER_ORDER = 10
