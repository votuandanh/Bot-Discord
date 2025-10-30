
import discord
from discord.ext import commands
from discord import app_commands
from utils.checks import is_target_channel_check_func

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Hiển thị bảng hướng dẫn các lệnh của bot.")
    @app_commands.check(is_target_channel_check_func)
    async def help(self, interaction: discord.Interaction):
        """Gửi một tin nhắn embed với danh sách các lệnh có sẵn."""
        
        embed = discord.Embed(
            title="📖 Bảng Hướng Dẫn Game RPG 📖",
            description="Chào mừng bạn đến với thế giới RPG! Dưới đây là các lệnh bạn có thể sử dụng:",
            color=discord.Color.from_rgb(127, 0, 255) # Một màu tím đẹp mắt
        )

        # Phần Nhân Vật
        embed.add_field(
            name="👤 Nhân Vật",
            value="/taonhanvat: Tạo nhân vật mới để bắt đầu hành trình.\n" 
                  "/thongtin: Xem chi tiết chỉ số, cấp độ và trang bị của bạn.",
            inline=False
        )

        # Phần Hành Động
        embed.add_field(
            name="⚔️ Hành Động",
            value="/phieuluu: Bắt đầu cuộc phiêu lưu, chiến đấu với quái vật để nhận EXP và vàng.",
            inline=False
        )

        # Phần Kinh Tế
        embed.add_field(
            name="💰 Kinh Tế",
            value="/shop: Mua vũ khí, áo giáp và các vật phẩm khác.\n" 
                  "/kho: Xem các vật phẩm bạn đang sở hữu.\n" 
                  "/trangbi: Trang bị hoặc thay đổi vũ khí/áo giáp.",
            inline=False
        )
        
        embed.set_footer(text="Chúc bạn có một cuộc phiêu lưu vui vẻ!")
        embed.set_thumbnail(url="https://i.imgur.com/R2v5M2s.png") # Một icon sách phép thuật

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Hàm setup để bot tải cog."""
    await bot.add_cog(HelpCog(bot))
