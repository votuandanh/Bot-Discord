import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from utils.database import init_db
import logging # Import logging module

# --- Cấu hình Logging ---
# Cấu hình logger gốc của Python
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

# Cấu hình logger cho thư viện discord để giảm bớt thông tin không cần thiết
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.WARNING)

# --- KHỞI TẠO ---

# Tải các biến môi trường từ file .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID_STR = os.getenv("TARGET_CHANNEL_ID")
TARGET_CHANNEL_ID = int(TARGET_CHANNEL_ID_STR) if TARGET_CHANNEL_ID_STR else None

# Khởi tạo cơ sở dữ liệu
init_db()
logging.info("Cơ sở dữ liệu đã được khởi tạo.")

# --- CÀI ĐẶT BOT ---

class MyBot(commands.Bot):
    def __init__(self):
        # Intents tối thiểu cho bot chỉ dùng Slash Command
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(
            command_prefix="/",
            intents=intents
        )
        self.target_channel_id = TARGET_CHANNEL_ID # Lưu ID kênh vào bot instance

    async def setup_hook(self):
        logging.info("Đang tìm và tải các cog...")
        # Tìm và tải tất cả các cog trong thư mục 'cogs'
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                cog_name = f'cogs.{filename[:-3]}'
                try:
                    await self.load_extension(cog_name)
                    logging.info(f"Đã tải cog thành công: {filename}")
                except Exception as e:
                    logging.error(f"Không thể tải cog {filename}: {e}")

        logging.info("Đang đồng bộ hóa cây lệnh...")
        # Đồng bộ hóa cây lệnh
        try:
            synced = await self.tree.sync()
            logging.info(f"Đã đồng bộ {len(synced)} lệnh")
        except Exception as e:
            logging.error(f"Không thể đồng bộ lệnh: {e}")

    async def on_ready(self):
        logging.info(f"Đã đăng nhập với tên {self.user}!")

bot = MyBot()

# --- CHẠY BOT ---

if __name__ == "__main__":
    if TOKEN is None:
        logging.error("Không tìm thấy DISCORD_TOKEN trong file .env")
    elif TARGET_CHANNEL_ID is None:
        logging.error("Không tìm thấy TARGET_CHANNEL_ID trong file .env")
    else:
        bot.run(TOKEN)