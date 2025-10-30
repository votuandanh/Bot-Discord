import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from utils.database import get_db_connection
from utils.checks import is_target_channel_check_func

# --- DANH SÁCH VẬT PHẨM TRONG CỬA HÀNG ---
SHOP_ITEMS = {
    "sword1": {"name": "Kiếm Gỗ", "price": 50, "type": "weapon", "atk_boost": 5},
    "potion1": {"name": "Bình Máu Nhỏ", "price": 20, "type": "consumable", "hp_restore": 50},
    "armor1": {"name": "Áo Vải", "price": 80, "type": "armor", "def_boost": 3},
}

# --- UI CHO CỬA HÀNG ---

class ShopView(discord.ui.View):
    def __init__(self, player_id):
        super().__init__(timeout=180)
        self.player_id = player_id
        self.selected_item_key = None

        # Tạo Select Menu từ danh sách vật phẩm
        select_options = []
        for key, item in SHOP_ITEMS.items():
            select_options.append(
                discord.SelectOption(label=f"{item['name']} ({item['price']} Vàng)", value=key)
            )
        
        item_select = discord.ui.Select(placeholder="Chọn một vật phẩm để mua...", options=select_options)
        item_select.callback = self.on_item_select
        self.add_item(item_select)

    async def on_item_select(self, interaction: discord.Interaction):
        # Lưu vật phẩm được chọn và hiển thị nút mua
        self.selected_item_key = interaction.data["values"][0]
        selected_item = SHOP_ITEMS[self.selected_item_key]

        # Xóa nút mua cũ nếu có
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label.startswith("Mua"):
                self.remove_item(item)

        # Tạo nút mua mới
        buy_button = discord.ui.Button(
            label=f"Mua {selected_item['name']}", 
            style=discord.ButtonStyle.green,
            custom_id=f"buy_{self.selected_item_key}"
        )
        buy_button.callback = self.on_buy_button_click
        self.add_item(buy_button)

        await interaction.response.edit_message(view=self)

    async def on_buy_button_click(self, interaction: discord.Interaction):
        if not self.selected_item_key:
            await interaction.response.send_message("Lỗi: Chưa chọn vật phẩm.", ephemeral=True)
            return

        item_to_buy = SHOP_ITEMS[self.selected_item_key]
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Kiểm tra số dư của người chơi
        cursor.execute("SELECT gold FROM players WHERE id = ?", (self.player_id,))
        player_gold = cursor.fetchone()['gold']

        if player_gold >= item_to_buy['price']:
            # 2. Trừ vàng
            new_gold = player_gold - item_to_buy['price']
            cursor.execute("UPDATE players SET gold = ? WHERE id = ?", (new_gold, self.player_id))

            # 3. Thêm vật phẩm vào kho đồ
            cursor.execute(
                "INSERT INTO inventory (player_id, item_name, item_type) VALUES (?, ?, ?)",
                (self.player_id, item_to_buy['name'], item_to_buy['type'])
            )
            conn.commit()
            message = f"Bạn đã mua thành công **{item_to_buy['name']}**!"
        else:
            message = "Bạn không đủ vàng để mua vật phẩm này!"
        
        conn.close()
        await interaction.response.send_message(message, ephemeral=True)


# --- UI CHO TRANG BỊ ---

class EquipView(discord.ui.View):
    def __init__(self, player_id):
        super().__init__(timeout=180)
        self.player_id = player_id

        # Tạo Select Menu từ kho đồ của người chơi
        conn = get_db_connection()
        cursor = conn.cursor()
        # Chỉ lấy các vật phẩm có thể trang bị (vũ khí, giáp)
        cursor.execute("SELECT inventory_id, item_name, item_type, is_equipped FROM inventory WHERE player_id = ? AND item_type IN ('weapon', 'armor')", (player_id,))
        equippable_items = cursor.fetchall()
        conn.close()

        select_options = []
        if not equippable_items:
            select_options.append(discord.SelectOption(label="Bạn không có trang bị nào.", value="none", default=True))
        else:
            for item in equippable_items:
                equip_status = " (Đã trang bị)" if item['is_equipped'] else ""
                select_options.append(
                    discord.SelectOption(label=f"{item['item_name']}{equip_status}", value=str(item['inventory_id']))
                )
        
        item_select = discord.ui.Select(placeholder="Chọn một vật phẩm để trang bị...", options=select_options)
        item_select.callback = self.on_item_select
        self.add_item(item_select)

    async def on_item_select(self, interaction: discord.Interaction):
        selected_inventory_id = int(interaction.data["values"][0])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Lấy loại vật phẩm của item được chọn
        cursor.execute("SELECT item_type FROM inventory WHERE inventory_id = ?", (selected_inventory_id,))
        item_type = cursor.fetchone()['item_type']

        # Bỏ trang bị tất cả các vật phẩm cùng loại
        cursor.execute("UPDATE inventory SET is_equipped = 0 WHERE player_id = ? AND item_type = ?", (self.player_id, item_type))

        # Trang bị vật phẩm mới
        cursor.execute("UPDATE inventory SET is_equipped = 1 WHERE inventory_id = ?", (selected_inventory_id,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Bạn đã trang bị thành công vật phẩm.", ephemeral=True)
        
        # Cập nhật lại view để hiển thị trạng thái mới (tùy chọn)
        new_view = EquipView(self.player_id)
        await interaction.edit_original_response(view=new_view)


# --- ĐỊNH NGHĨA COG ---

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Mở cửa hàng để mua vật phẩm.")
    @app_commands.check(is_target_channel_check_func)
    async def shop(self, interaction: discord.Interaction):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM players WHERE id = ?", (interaction.user.id,))
        player = cursor.fetchone()
        conn.close()

        if not player:
            await interaction.response.send_message("Bạn cần tạo nhân vật trước khi vào shop! Dùng `/taonhanvat`.", ephemeral=True)
            return

        embed = discord.Embed(title="Cửa Hàng Rèn", description="Chào mừng đến với cửa hàng! Hãy chọn một món đồ.", color=discord.Color.dark_gold())
        await interaction.response.send_message(embed=embed, view=ShopView(interaction.user.id), ephemeral=True)

    @app_commands.command(name="kho", description="Kiểm tra kho đồ của bạn.")
    @app_commands.check(is_target_channel_check_func)
    async def inventory(self, interaction: discord.Interaction):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT item_name, COUNT(*) as quantity FROM inventory WHERE player_id = ? GROUP BY item_name", (interaction.user.id,))
        items = cursor.fetchall()
        conn.close()

        if not items:
            await interaction.response.send_message("Kho đồ của bạn trống rỗng.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Kho Đồ của {interaction.user.display_name}", color=discord.Color.dark_purple())
        
        description = ""
        for item in items:
            description += f"- **{item['item_name']}** (Số lượng: {item['quantity']})\n"
        
        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="trangbi", description="Trang bị vật phẩm từ kho đồ.")
    @app_commands.check(is_target_channel_check_func)
    async def equip(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Trang Bị", description="Chọn một vật phẩm từ kho của bạn để trang bị.", color=discord.Color.dark_blue())
        view = EquipView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))