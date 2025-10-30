import discord
import logging

# Hàm kiểm tra tùy chỉnh để đảm bảo lệnh chỉ chạy trong kênh được chỉ định
async def is_target_channel_check_func(interaction: discord.Interaction) -> bool:
    if not hasattr(interaction.client, 'target_channel_id'):
        logging.error("Bot instance thiếu thuộc tính 'target_channel_id'. Không thể kiểm tra kênh.")
        return False

    target_id = interaction.client.target_channel_id
    if interaction.channel_id == target_id:
        return True
    else:
        # Đảm bảo rằng chúng ta chỉ gửi phản hồi nếu chưa có phản hồi nào được gửi đi
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Bot chỉ hoạt động trong kênh <#{target_id}>.", ephemeral=True)
        return False
