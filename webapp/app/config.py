import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key"
    DATABASE = os.environ.get("DATABASE") or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "instance", "catalog.db"
    )
