
import discord
from discord.ext import commands
from discord import app_commands
from utils.database import get_db_connection
import logging

# --- HÀM KIỂM TRA CHỦ BOT ---
async def is_bot_owner(interaction: discord.Interaction) -> bool:
    """Kiểm tra xem người dùng có phải là chủ của bot hay không."""
    # bot.is_owner() sẽ tự động kiểm tra dựa trên thông tin của ứng dụng bot
    if await interaction.client.is_owner(interaction.user):
        return True
    else:
        # Gửi một thông báo lỗi riêng tư nếu không phải chủ bot
        await interaction.response.send_message("Lệnh này chỉ dành cho chủ bot.", ephemeral=True)
        return False

# --- ĐỊNH NGHĨA COG QUẢN TRỊ ---

# Sử dụng Group để nhóm các lệnh admin lại với nhau
class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Tạo một nhóm lệnh /admin
    admin_group = app_commands.Group(name="admin", description="Các lệnh quản trị chỉ dành cho chủ bot.")

    @admin_group.command(name="addgold", description="Thêm vàng cho một người chơi.")
    @app_commands.describe(
        user="Người chơi bạn muốn thêm vàng.",
        amount="Số lượng vàng muốn thêm."
    )
    @app_commands.check(is_bot_owner) # Áp dụng check chủ bot
    async def add_gold(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[int, 1]):
        """Lệnh thêm vàng cho người chơi."""
        if amount <= 0:
            await interaction.response.send_message("Số vàng phải là một số dương.", ephemeral=True)
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Kiểm tra xem người chơi có tồn tại không
            cursor.execute("SELECT gold FROM players WHERE id = ?", (user.id,))
            player = cursor.fetchone()

            if player is None:
                await interaction.response.send_message(f"Người chơi {user.mention} không tồn tại trong cơ sở dữ liệu.", ephemeral=True)
                conn.close()
                return

            # Cập nhật vàng cho người chơi
            new_gold = player['gold'] + amount
            cursor.execute("UPDATE players SET gold = ? WHERE id = ?", (new_gold, user.id))
            conn.commit()
            conn.close()

            logging.info(f"Admin {interaction.user.name} đã thêm {amount} vàng cho {user.name}.")
            await interaction.response.send_message(f"Đã thêm thành công {amount} vàng cho {user.mention}. Số dư mới: {new_gold} G.", ephemeral=True)

        except Exception as e:
            logging.error(f"Lỗi khi thực hiện lệnh add_gold: {e}")
            await interaction.response.send_message(f"Đã xảy ra lỗi: {e}", ephemeral=True)


# --- UI XÁC NHẬN XÓA NHÂN VẬT ---
class ResetConfirmView(discord.ui.View):
    def __init__(self, author: discord.User, target_user: discord.User):
        super().__init__(timeout=60)
        self.author = author
        self.target_user = target_user
        self.value = None

    # Chỉ người dùng ban đầu mới có thể tương tác
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Đây không phải là nút của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Xác Nhận Xóa", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Xóa tất cả vật phẩm của người chơi khỏi kho đồ
            cursor.execute("DELETE FROM inventory WHERE player_id = ?", (self.target_user.id,))
            
            # Xóa người chơi khỏi bảng players
            cursor.execute("DELETE FROM players WHERE id = ?", (self.target_user.id,))
            
            conn.commit()
            conn.close()

            logging.info(f"Admin {self.author.name} đã xóa nhân vật của {self.target_user.name}.")
            await interaction.response.edit_message(content=f"Đã xóa thành công nhân vật của {self.target_user.mention}.", view=None)

        except Exception as e:
            logging.error(f"Lỗi khi xóa nhân vật: {e}")
            await interaction.response.edit_message(content=f"Đã xảy ra lỗi khi xóa nhân vật: {e}", view=None)
        
        self.stop()

    @discord.ui.button(label="Hủy", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Hành động xóa đã được hủy.", view=None)
        self.stop()

# --- COG ---
class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Tạo một nhóm lệnh /admin
    admin_group = app_commands.Group(name="admin", description="Các lệnh quản trị chỉ dành cho chủ bot.")

    @admin_group.command(name="addgold", description="Thêm vàng cho một người chơi.")
    @app_commands.describe(
        user="Người chơi bạn muốn thêm vàng.",
        amount="Số lượng vàng muốn thêm."
    )
    @app_commands.check(is_bot_owner) # Áp dụng check chủ bot
    async def add_gold(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[int, 1]):
        """Lệnh thêm vàng cho người chơi."""
        if amount <= 0:
            await interaction.response.send_message("Số vàng phải là một số dương.", ephemeral=True)
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Kiểm tra xem người chơi có tồn tại không
            cursor.execute("SELECT gold FROM players WHERE id = ?", (user.id,))
            player = cursor.fetchone()

            if player is None:
                await interaction.response.send_message(f"Người chơi {user.mention} không tồn tại trong cơ sở dữ liệu.", ephemeral=True)
                conn.close()
                return

            # Cập nhật vàng cho người chơi
            new_gold = player['gold'] + amount
            cursor.execute("UPDATE players SET gold = ? WHERE id = ?", (new_gold, user.id))
            conn.commit()
            conn.close()

            logging.info(f"Admin {interaction.user.name} đã thêm {amount} vàng cho {user.name}.")
            await interaction.response.send_message(f"Đã thêm thành công {amount} vàng cho {user.mention}. Số dư mới: {new_gold} G.", ephemeral=True)

        except Exception as e:
            logging.error(f"Lỗi khi thực hiện lệnh add_gold: {e}")
            await interaction.response.send_message(f"Đã xảy ra lỗi: {e}", ephemeral=True)

    @admin_group.command(name="resetcharacter", description="Xóa hoàn toàn một nhân vật khỏi cơ sở dữ liệu.")
    @app_commands.describe(user="Người chơi bạn muốn xóa nhân vật.")
    @app_commands.check(is_bot_owner)
    async def reset_character(self, interaction: discord.Interaction, user: discord.User):
        """Lệnh xóa nhân vật với bước xác nhận."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM players WHERE id = ?", (user.id,))
        player = cursor.fetchone()
        conn.close()

        if player is None:
            await interaction.response.send_message(f"Người chơi {user.mention} không tồn tại.", ephemeral=True)
            return

        view = ResetConfirmView(author=interaction.user, target_user=user)
        embed = discord.Embed(
            title="⚠️ Cảnh Báo Xóa Nhân Vật ⚠️",
            description=f"Bạn có chắc chắn muốn xóa vĩnh viễn nhân vật **{player['name']}** của {user.mention} không?\n\n**Hành động này không thể hoàn tác.** Toàn bộ dữ liệu, bao gồm cấp độ, chỉ số và vật phẩm sẽ bị xóa.",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Hàm setup để bot tải cog."""
    await bot.add_cog(AdminCog(bot))
