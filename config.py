from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATABASE_DIR / "reading_list.db"
BOOKS_CSV_PATH = DATA_DIR / "Books_df.csv"
DEBUG = True
SECRET_KEY = "cop4710-dev-key"
