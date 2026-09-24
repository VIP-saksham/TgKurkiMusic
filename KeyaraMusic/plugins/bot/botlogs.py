# KeyaraMusic — log group watcher
#
# Log group me sirf bot ki zaroori events:
#   - bot kisi naye group me add hua (branded start art ke saath)
#   - bot kisi group se remove hua
#
# Helpers ka auto-join/leave aur faltu welcome spam yahan se hata diya gaya hai.

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import LOG_GROUP_ID, START_IMG_URL
from KeyaraMusic import app
from KeyaraMusic.utils.database import add_served_chat, delete_served_chat


@app.on_message(filters.new_chat_members, group=-10)
async def join_watcher(_, message):
    try:
        for members in message.new_chat_members:
            if members.id == app.id:
                count = await app.get_chat_members_count(message.chat.id)
                username = (
                    f"@{message.chat.username}"
                    if message.chat.username
                    else "Private Group"
                )

                msg = (
                    "#NewGroup\n\n"
                    f"Chat Name: {message.chat.title}\n"
                    f"Chat ID: <code>{message.chat.id}</code>\n"
                    f"Chat Username: {username}\n"
                    f"Group Members: {count}\n"
                    f"Added By: {message.from_user.mention if message.from_user else 'Unknown'}"
                )

                await app.send_photo(
                    LOG_GROUP_ID,
                    photo=START_IMG_URL,
                    caption=msg,
                )
                await add_served_chat(message.chat.id)
    except Exception as e:
        print(f"Error: {e}")


@app.on_message(filters.left_chat_member, group=-12)
async def on_left_chat_member(_, message: Message):
    try:
        left_chat_member = message.left_chat_member
        if left_chat_member and left_chat_member.id == app.id:
            remove_by = (
                message.from_user.mention
                if message.from_user
                else "Unknown User"
            )
            left = (
                "#LeftGroup\n\n"
                f"Chat Title: {message.chat.title}\n"
                f"Chat ID: <code>{message.chat.id}</code>\n"
                f"Removed By: {remove_by}\n"
                f"Bot: @{app.username}"
            )
            await app.send_photo(LOG_GROUP_ID, photo=START_IMG_URL, caption=left)
            await delete_served_chat(message.chat.id)
    except Exception:
        return
