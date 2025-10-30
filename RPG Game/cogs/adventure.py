import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random # Import random module
from utils.database import get_db_connection
from utils.checks import is_target_channel_check_func
from cogs.economy import SHOP_ITEMS

# --- CÁC THÀNH PHẦN UI ĐỂ TẠO NHÂN VẬT --- (Tên comment này không còn chính xác, nhưng giữ để tránh thay đổi quá nhiều)

# Định nghĩa các loại quái vật
MONSTERS = {
    "Slime": {"hp": 30, "atk": 5, "exp": 10, "gold": 5},
    "Goblin": {"hp": 50, "atk": 8, "exp": 20, "gold": 10},
    "Wolf": {"hp": 40, "atk": 7, "exp": 15, "gold": 8},
}

# View cho các hành động trong trận chiến
class CombatView(discord.ui.View):
    def __init__(self, player_data, monster_name, monster_stats):
        super().__init__(timeout=180)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        bonus_atk = 0
        bonus_def = 0

        # Lấy ID vật phẩm đang trang bị từ player_data
        weapon_equipped_id = player_data['weapon_equipped_id']
        armor_equipped_id = player_data['armor_equipped_id']

        # Lấy thông tin vũ khí đang trang bị
        if weapon_equipped_id:
            cursor.execute("SELECT item_name FROM inventory WHERE inventory_id = ?", (weapon_equipped_id,))
            weapon_item = cursor.fetchone()
            if weapon_item:
                equipped_weapon_name = weapon_item['item_name']
                for key, shop_item in SHOP_ITEMS.items():
                    if shop_item['name'] == equipped_weapon_name:
                        bonus_atk += shop_item.get('atk_boost', 0)
                        break

        # Lấy thông tin giáp đang trang bị
        if armor_equipped_id:
            cursor.execute("SELECT item_name FROM inventory WHERE inventory_id = ?", (armor_equipped_id,))
            armor_item = cursor.fetchone()
            if armor_item:
                equipped_armor_name = armor_item['item_name']
                for key, shop_item in SHOP_ITEMS.items():
                    if shop_item['name'] == equipped_armor_name:
                        bonus_def += shop_item.get('def_boost', 0)
                        break
        conn.close()
        
        # Cập nhật chỉ số thực tế cho trận đấu
        self.player = dict(player_data) # Tạo một bản sao để chỉnh sửa
        self.player['atk'] += bonus_atk
        self.player['def'] += bonus_def

        self.monster_name = monster_name
        self.monster_stats = monster_stats
        self.player_current_hp = self.player['hp']
        self.monster_current_hp = self.monster_stats['hp']

    def _get_combat_embed(self, log_message=""):
        embed = discord.Embed(
            title=f"Trận Chiến: {self.player['name']} vs {self.monster_name}",
            color=discord.Color.red()
        )
        embed.add_field(name=f"{self.player['name']} HP", value=f"{self.player_current_hp}/{self.player['hp']}", inline=True)
        embed.add_field(name=f"{self.monster_name} HP", value=f"{self.monster_current_hp}/{self.monster_stats['hp']}", inline=True)
        if log_message:
            embed.add_field(name="Nhật ký", value=log_message, inline=False)
        return embed

    async def _end_combat(self, interaction: discord.Interaction, message: str, won: bool = False):
        # Lấy embed kết quả trận đấu
        embed = self._get_combat_embed()
        level_up_message = ""

        if won:
            embed.color = discord.Color.green()
            conn = get_db_connection()
            cursor = conn.cursor()

            # Lấy dữ liệu người chơi hiện tại
            current_player = self.player
            new_exp = current_player['exp'] + self.monster_stats['exp']
            new_gold = current_player['gold'] + self.monster_stats['gold']
            current_level = current_player['level']
            
            # --- LOGIC LÊN CẤP ---
            print(f"--- DEBUG: Bắt đầu kiểm tra lên cấp cho người chơi {self.player['id']} ---")
            print(f"DEBUG: EXP hiện tại: {current_player['exp']}, EXP nhận được: {self.monster_stats['exp']}, Tổng EXP mới: {new_exp}")
            print(f"DEBUG: Cấp độ hiện tại: {current_level}")

            exp_needed = current_level * 100
            print(f"DEBUG: EXP cần để lên cấp: {exp_needed}")

            while new_exp >= exp_needed:
                print(f"DEBUG: Đủ EXP để lên cấp! ({new_exp} >= {exp_needed})")
                # Trừ exp, tăng level
                new_exp -= exp_needed
                current_level += 1
                level_up_message += f"\n**Chúc mừng! Bạn đã đạt đến cấp độ {current_level}!** 🎉"
                print(f"DEBUG: Đã lên cấp {current_level}. EXP còn lại: {new_exp}")

                # Tăng chỉ số dựa trên class
                if current_player['class'] == 'Warrior':
                    current_player['hp'] += 20
                    current_player['mp'] += 5
                    current_player['atk'] += 3
                    current_player['def'] += 2
                elif current_player['class'] == 'Mage':
                    current_player['hp'] += 10
                    current_player['mp'] += 15
                    current_player['atk'] += 4
                    current_player['def'] += 1
                elif current_player['class'] == 'Archer':
                    current_player['hp'] += 15
                    current_player['mp'] += 10
                    current_player['atk'] += 3
                    current_player['def'] += 2
                
                # Cập nhật exp cần cho level tiếp theo
                exp_needed = current_level * 100

            # Cập nhật CSDL với tất cả các thay đổi
            cursor.execute("""
                UPDATE players 
                SET level = ?, exp = ?, gold = ?, hp = ?, mp = ?, atk = ?, def = ?
                WHERE id = ?
            """, (current_level, new_exp, new_gold, current_player['hp'], current_player['mp'], current_player['atk'], current_player['def'], self.player['id']))
            conn.commit()

            # Lấy dữ liệu người chơi mới nhất để cập nhật view
            cursor.execute("SELECT * FROM players WHERE id = ?", (self.player['id'],))
            self.player = dict(cursor.fetchone())
            conn.close()
        else:
            embed.color = discord.Color.dark_red()

        # Thêm thông báo vào embed và dừng view
        embed.description = message + level_up_message
        self.stop()

        # Tạo lại view phiêu lưu với dữ liệu người chơi đã cập nhật
        adventure_view = AdventureSelectView(self.player)
        await interaction.response.edit_message(content="Cuộc chiến đã kết thúc! Bạn muốn làm gì tiếp theo?", embed=embed, view=adventure_view)

    @discord.ui.button(label="⚔️ Tấn Công", style=discord.ButtonStyle.red)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Người chơi tấn công
        player_damage = self.player['atk'] # Sát thương cơ bản, có thể phức tạp hơn
        self.monster_current_hp -= player_damage
        log = f"💥 {self.player['name']} gây {player_damage} sát thương cho {self.monster_name}.\n"

        if self.monster_current_hp <= 0:
            await self._end_combat(interaction, log + f"🎉 {self.monster_name} đã bị đánh bại! Bạn nhận được {self.monster_stats['exp']} EXP và {self.monster_stats['gold']} Vàng.", won=True)
            return

        # Quái vật tấn công lại
        # Thêm một chút ngẫu nhiên vào sát thương của quái vật
        monster_damage = max(0, self.monster_stats['atk'] - self.player['def'])
        monster_damage = random.randint(int(monster_damage * 0.8), int(monster_damage * 1.2))
        self.player_current_hp -= monster_damage
        log += f"🩸 {self.monster_name} gây {monster_damage} sát thương cho {self.player['name']}."

        if self.player_current_hp <= 0:
            await self._end_combat(interaction, log + f"☠️ {self.player['name']} đã bị đánh bại!", won=False)
            return

        # Cập nhật trạng thái trận chiến
        await interaction.response.edit_message(embed=self._get_combat_embed(log), view=self)

    @discord.ui.button(label="🏃 Chạy Trốn", style=discord.ButtonStyle.grey)
    async def flee_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        flee_chance = random.randint(1, 100)
        if flee_chance > 30: # 70% thành công
            await self._end_combat(interaction, "Bạn đã chạy trốn thành công!", won=False)
        else:
            # Chạy trốn thất bại, quái vật tấn công
            log = "Chạy trốn thất bại! "
            monster_damage = max(0, self.monster_stats['atk'] - self.player['def'])
            self.player_current_hp -= monster_damage
            log += f"🩸 {self.monster_name} gây {monster_damage} sát thương cho bạn."

            if self.player_current_hp <= 0:
                await self._end_combat(interaction, log + f"☠️ {self.player['name']} đã bị đánh bại!", won=False)
            else:
                await interaction.response.edit_message(embed=self._get_combat_embed(log), view=self)


# View cho việc chọn khu vực phiêu lưu
class AdventureSelectView(discord.ui.View):
    def __init__(self, player_data):
        super().__init__(timeout=180)
        self.player = player_data

    async def _start_encounter(self, interaction: discord.Interaction, area_name: str):
        monster_name = random.choice(list(MONSTERS.keys()))
        monster_stats = MONSTERS[monster_name]

        # Khởi tạo trận chiến
        combat_view = CombatView(self.player, monster_name, monster_stats)
        embed = combat_view._get_combat_embed()
        await interaction.response.edit_message(
            content=f"Một {monster_name} hoang dã xuất hiện ở {area_name}!",
            embed=embed,
            view=combat_view
        )

    @discord.ui.button(label="🌲 Săn Quái Rừng", style=discord.ButtonStyle.green)
    async def forest_hunt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._start_encounter(interaction, "Khu Rừng")

    @discord.ui.button(label="⛰️ Thám Hiểm Hang Động", style=discord.ButtonStyle.blurple)
    async def cave_explore(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._start_encounter(interaction, "Hang Động")

    @discord.ui.button(label="🔙 Quay Về", style=discord.ButtonStyle.red)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Bạn đã quay về an toàn.", view=None)


class AdventureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="phieuluu", description="Bắt đầu một cuộc phiêu lưu mới.")
    @app_commands.check(is_target_channel_check_func)
    async def adventure(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE id = ?", (user_id,))
        player = cursor.fetchone()
        player_dict = dict(player) if player else None # Chuyển Row thành dict
        conn.close()

        if player_dict:
            await interaction.response.send_message("Chọn khu vực bạn muốn phiêu lưu:", view=AdventureSelectView(player_dict), ephemeral=True)
        else:
            await interaction.response.send_message("Bạn chưa có nhân vật! Hãy dùng lệnh `/taonhanvat` để tạo một nhân vật mới.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdventureCog(bot))
