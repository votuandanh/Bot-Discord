import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from utils.database import get_db_connection
from utils.checks import is_target_channel_check_func
from cogs.economy import SHOP_ITEMS # Import SHOP_ITEMS để tra cứu chỉ số

# --- UI CHO THÔNG TIN NHÂN VẬT ---

def create_player_embed(player_data, user_avatar_url):
    """Tạo một Embed từ dữ liệu người chơi, bao gồm cả chỉ số từ trang bị."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Lấy các vật phẩm đã trang bị
    cursor.execute("SELECT item_name FROM inventory WHERE player_id = ? AND is_equipped = 1", (player_data['id'],))
    equipped_items = cursor.fetchall()
    conn.close()

    bonus_atk = 0
    bonus_def = 0
    equipped_names = []

    for item_row in equipped_items:
        item_name = item_row['item_name']
        equipped_names.append(item_name)
        # Tìm vật phẩm trong SHOP_ITEMS để lấy chỉ số
        for key, shop_item in SHOP_ITEMS.items():
            if shop_item['name'] == item_name:
                bonus_atk += shop_item.get('atk_boost', 0)
                bonus_def += shop_item.get('def_boost', 0)
                break

    embed = discord.Embed(
        title=f"Thông Tin Nhân Vật: {player_data['name']}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=user_avatar_url)
    embed.add_field(name="Lớp Nhân Vật", value=player_data['class'], inline=True)
    embed.add_field(name="Cấp Độ", value=player_data['level'], inline=True)
    embed.add_field(name="Kinh Nghiệm (EXP)", value=f"{player_data['exp']} / {player_data['level'] * 100}", inline=False)
    embed.add_field(name="HP (Máu)", value=f"{player_data['hp']}", inline=True)
    embed.add_field(name="MP (Năng lượng)", value=f"{player_data['mp']}", inline=True)
    embed.add_field(name="Vàng", value=f"{player_data['gold']} G", inline=False)
    
    # Hiển thị chỉ số gốc và chỉ số cộng thêm
    atk_display = f"{player_data['atk']} (+{bonus_atk})" if bonus_atk > 0 else str(player_data['atk'])
    def_display = f"{player_data['def']} (+{bonus_def})" if bonus_def > 0 else str(player_data['def'])
    embed.add_field(name="Tấn Công (ATK)", value=atk_display, inline=True)
    embed.add_field(name="Phòng Thủ (DEF)", value=def_display, inline=True)

    if equipped_names:
        embed.add_field(name="Trang bị", value="\n".join(f"- {name}" for name in equipped_names), inline=False)

    embed.set_footer(text=f"ID: {player_data['id']}")
    return embed

class CharacterInfoView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300) # Tăng timeout lên 5 phút
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Chỉ người dùng ban đầu mới có thể tương tác
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Đây không phải là bảng thông tin của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔄 Cập nhật", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Lấy dữ liệu mới nhất
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE id = ?", (self.user_id,))
        player = cursor.fetchone()
        conn.close()

        if not player:
            await interaction.response.edit_message(content="Lỗi: Không tìm thấy nhân vật của bạn.", embed=None, view=None)
            return

        # 2. Tạo embed mới
        new_embed = create_player_embed(player, interaction.user.avatar.url if interaction.user.avatar else None)

        # 3. Cập nhật tin nhắn
        await interaction.response.edit_message(embed=new_embed, view=self)


# --- ĐỊNH NGHĨA COG ---

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="taonhanvat", description="Tạo một nhân vật RPG mới.")
    @app_commands.check(is_target_channel_check_func)
    async def create_character(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE id = ?", (user_id,))
        player = cursor.fetchone()
        conn.close()

        if player:
            await interaction.response.send_message("Bạn đã có nhân vật rồi!", ephemeral=True)
        else:
            await interaction.response.send_modal(CharacterNameModal())

    @app_commands.command(name="thongtin", description="Xem thông tin chi tiết về nhân vật của bạn.")
    @app_commands.check(is_target_channel_check_func)
    async def character_info(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE id = ?", (user_id,))
        player = cursor.fetchone()
        conn.close()

        if player:
            embed = create_player_embed(player, interaction.user.avatar.url if interaction.user.avatar else None)
            view = CharacterInfoView(user_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message("Bạn chưa có nhân vật! Hãy dùng lệnh `/taonhanvat` để tạo một nhân vật mới.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
