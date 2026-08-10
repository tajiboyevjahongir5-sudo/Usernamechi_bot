import os

with open('requirements.txt', 'w', encoding='utf-8') as f:
    f.write('aiogram>=3.3.0\ntelethon>=1.33.1\naiosqlite>=0.19.0\npython-dotenv>=1.0.0\n')

with open('.env.example', 'w', encoding='utf-8') as f:
    f.write('BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11\nADMIN_CHANNEL=-1001234567890\nPAYMENT_CARD=8600123456789012\nAPI_ID=1234567\nAPI_HASH=your_api_hash_here\n')

with open('config.py', 'w', encoding='utf-8') as f:
    f.write("""import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHANNEL = int(os.getenv("ADMIN_CHANNEL", "0"))
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
DB_PATH = "database/saas.db"

USERNAME_PRICE = 5000  # 1 ta username narxi (so'm)
""")
print("Files created")
