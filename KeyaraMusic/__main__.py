# Copyright (c) 2025 Nand Yaduwanshi <NoxxOP>
# Location: Supaul, Bihar
#
# All rights reserved.
#
# This code is the intellectual property of Nand Yaduwanshi.
# You are not allowed to copy, modify, redistribute, or use this
# code for commercial or personal projects without explicit permission.
#
# Allowed:
# - Forking for personal learning
# - Submitting improvements via pull requests
#
# Not Allowed:
# - Claiming this code as your own
# - Re-uploading without credit or permission
# - Selling or using commercially
#
# Contact for permissions:
# Email: badboy809075@gmail.com


import asyncio
import importlib
import os
import sys
from pyrogram import idle
from pyrogram.types import BotCommand
from pytgcalls.exceptions import NoActiveGroupCall
from pyrogram.errors import FloodWait
import config
from KeyaraMusic import LOGGER, app, userbot
from KeyaraMusic.core.call import Nand
from KeyaraMusic.misc import sudo
from KeyaraMusic.plugins import ALL_MODULES
from KeyaraMusic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

COMMANDS = [
    BotCommand("start", "❖ sᴛᴀʀᴛ ʙᴏᴛ • ᴛᴏ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ"),
    BotCommand("help", "❖ ʜᴇʟᴘ ᴍᴇɴᴜ • ɢᴇᴛ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs ᴀɴᴅ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ"),
    BotCommand("ping", "❖ ᴘɪɴɢ ʙᴏᴛ • ᴄʜᴇᴄᴋ ᴘɪɴɢ ᴀɴᴅ sʏsᴛᴇᴍ sᴛᴀᴛs"),
    BotCommand("play", "❖ ᴘʟᴀʏ ᴀᴜᴅɪᴏ ᴏɴ ᴠᴄ • ᴛᴏ ᴘʟᴀʏ ᴀɴʏ ᴀᴜᴅɪᴏ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ"),
    BotCommand("vplay", "❖ ᴘʟᴀʏ ᴠɪᴅᴇᴏ ᴏɴ ᴠᴄ • ᴛᴏ sᴛʀᴇᴀᴍ ᴀɴʏ ᴠɪᴅᴇᴏ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ"),
    BotCommand("playrtmps", "❖ ᴘʟᴀʏ ʟɪᴠᴇ ᴠɪᴅᴇᴏ • sᴛʀᴇᴀᴍ ʟɪᴠᴇ ᴠɪᴅᴇᴏ ᴄᴏɴᴛᴇɴᴛ"),
    BotCommand("playforce", "❖ ғᴏʀᴄᴇ ᴘʟᴀʏ ᴀᴜᴅɪᴏ • ғᴏʀᴄᴇ ᴘʟᴀʏ ᴀɴʏ ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋ"),
    BotCommand("vplayforce", "❖ ғᴏʀᴄᴇ ᴘʟᴀʏ ᴠɪᴅᴇᴏ • ғᴏʀᴄᴇ ᴘʟᴀʏ ᴀɴʏ ᴠɪᴅᴇᴏ ᴛʀᴀᴄᴋ"),
    BotCommand("pause", "❖ ᴘᴀᴜsᴇ sᴛʀᴇᴀᴍ • ᴘᴀᴜsᴇ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ sᴛʀᴇᴀᴍ"),
    BotCommand("resume", "❖ ʀᴇsᴜᴍᴇ sᴛʀᴇᴀᴍ • ʀᴇsᴜᴍᴇ ᴛʜᴇ ᴘᴀᴜsᴇᴅ sᴛʀᴇᴀᴍ"),
    BotCommand("skip", "❖ sᴋɪᴘ ᴛʀᴀᴄᴋ • sᴋɪᴘ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ᴛʀᴀᴄᴋ"),
    BotCommand("end", "❖ ᴇɴᴅ sᴛʀᴇᴀᴍ • sᴛᴏᴘ ᴛʜᴇ ᴏɴɢᴏɪɴɢ sᴛʀᴇᴀᴍ"),
    BotCommand("stop", "❖ sᴛᴏᴘ sᴛʀᴇᴀᴍ • sᴛᴏᴘ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ sᴛʀᴇᴀᴍ"),
    BotCommand("queue", "❖ sʜᴏᴡ ǫᴜᴇᴜᴇ • ᴅɪsᴘʟᴀʏ ᴛʀᴀᴄᴋ ǫᴜᴇᴜᴇ ʟɪsᴛ"),
    BotCommand("auth", "❖ ᴀᴅᴅ ᴀᴜᴛʜ ᴜsᴇʀ • ᴀᴅᴅ ᴜsᴇʀ ᴛᴏ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ʟɪsᴛ"),
    BotCommand("unauth", "❖ ʀᴇᴍᴏᴠᴇ ᴀᴜᴛʜ • ʀᴇᴍᴏᴠᴇ ᴜsᴇʀ ғʀᴏᴍ ᴀᴜᴛʜ ʟɪsᴛ"),
    BotCommand("authusers", "❖ ᴀᴜᴛʜ ʟɪsᴛ • sʜᴏᴡ ᴀʟʟ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀs"),
    BotCommand("cplay", "❖ ᴄʜᴀɴɴᴇʟ ᴀᴜᴅɪᴏ • ᴘʟᴀʏ ᴀᴜᴅɪᴏ ɪɴ ᴄʜᴀɴɴᴇʟ"),
    BotCommand("cvplay", "❖ ᴄʜᴀɴɴᴇʟ ᴠɪᴅᴇᴏ • ᴘʟᴀʏ ᴠɪᴅᴇᴏ ɪɴ ᴄʜᴀɴɴᴇʟ"),
    BotCommand("cplayforce", "❖ ᴄʜᴀɴɴᴇʟ ғᴏʀᴄᴇ ᴀᴜᴅɪᴏ • ғᴏʀᴄᴇ ᴘʟᴀʏ ɪɴ ᴄʜᴀɴɴᴇʟ"),
    BotCommand("cvplayforce", "❖ ᴄʜᴀɴɴᴇʟ ғᴏʀᴄᴇ ᴠɪᴅᴇᴏ • ғᴏʀᴄᴇ ᴠɪᴅᴇᴏ ɪɴ ᴄʜᴀɴɴᴇʟ"),
    BotCommand("channelplay", "❖ ᴄᴏɴɴᴇᴄᴛ ᴄʜᴀɴɴᴇʟ • ʟɪɴᴋ ɢʀᴏᴜᴘ ᴛᴏ ᴄʜᴀɴɴᴇʟ"),
    BotCommand("loop", "❖ ʟᴏᴏᴘ ᴍᴏᴅᴇ • ᴇɴᴀʙʟᴇ ᴏʀ ᴅɪsᴀʙʟᴇ ʟᴏᴏᴘ"),
    BotCommand("stats", "❖ ʙᴏᴛ sᴛᴀᴛs • sʜᴏᴡ ʙᴏᴛ sᴛᴀᴛɪsᴛɪᴄs"),
    BotCommand("shuffle", "❖ sʜᴜғғʟᴇ ǫᴜᴇᴜᴇ • ʀᴀɴᴅᴏᴍɪᴢᴇ ᴛʀᴀᴄᴋ ᴏʀᴅᴇʀ"),
    BotCommand("seek", "❖ sᴇᴇᴋ ғᴏʀᴡᴀʀᴅ • sᴋɪᴘ ᴛᴏ sᴘᴇᴄɪғɪᴄ ᴛɪᴍᴇ"),
    BotCommand("seekback", "❖ sᴇᴇᴋ ʙᴀᴄᴋᴡᴀʀᴅ • ɢᴏ ʙᴀᴄᴋ ᴛᴏ ᴘʀᴇᴠɪᴏᴜs ᴛɪᴍᴇ"),
    BotCommand("song", "❖ ᴅᴏᴡɴʟᴏᴀᴅ sᴏɴɢ • ɢᴇᴛ ᴍᴘ3 ᴏʀ ᴍᴘ4 ғɪʟᴇ"),
    BotCommand("speed", "❖ ᴀᴅᴊᴜsᴛ sᴘᴇᴇᴅ • ᴄʜᴀɴɢᴇ ᴘʟᴀʏʙᴀᴄᴋ sᴘᴇᴇᴅ ɪɴ ɢʀᴏᴜᴘ"),
    BotCommand("cspeed", "❖ ᴄʜᴀɴɴᴇʟ sᴘᴇᴇᴅ • ᴀᴅᴊᴜsᴛ sᴘᴇᴇᴅ ɪɴ ᴄʜᴀɴɴᴇʟ"),
    BotCommand("tagall", "❖ ᴛᴀɢ ᴀʟʟ • ᴍᴇɴᴛɪᴏɴ ᴇᴠᴇʀʏᴏɴᴇ ɪɴ ɢʀᴏᴜᴘ"),
]

async def setup_bot_commands():
    try:
        await app.set_bot_commands(COMMANDS)
        LOGGER("KeyaraMusic").info("Bot commands set successfully!")
        
    except Exception as e:
        LOGGER("KeyaraMusic").error(f"Failed to set bot commands: {str(e)}")

async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("Assistant client variables not defined, exiting...")
        exit()

    await sudo()

    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass

    await app.start()

    await setup_bot_commands()

    for all_module in ALL_MODULES:
        importlib.import_module("KeyaraMusic.plugins" + all_module)

    LOGGER("KeyaraMusic.plugins").info("Successfully Imported Modules...")

    await userbot.start()

    # Log group ka VC off ho to assistant se auto-start karo
    if config.LOG_GROUP_ID:
        try:
            from pyrogram.raw import functions as raw_funcs, types as raw_types
            peer = await userbot.one.resolve_peer(config.LOG_GROUP_ID)
            if hasattr(peer, "channel_id"):
                peer = raw_types.InputChannel(
                    channel_id=peer.channel_id, access_hash=peer.access_hash
                )
            await userbot.one.invoke(
                raw_funcs.channels.CreateGroupCall(
                    peer=peer,
                    random_id=int.from_bytes(os.urandom(4), "big"),
                    title="KurkiMusic",
                )
            )
            LOGGER(__name__).info("Log group me voice chat auto-start kar diya.")
            await asyncio.sleep(3)
        except Exception as e:
            LOGGER(__name__).warning(f"VC auto-start skip: {e}")

    # Channel cache (@teamjatayu): purane audios ko Mongo me index karo
    # (history sirf user account se read hoti hai — assistant use karo)
    try:
        from KeyaraMusic.core.channelcache import seed_from_channel
        if config.CACHE_UPLOAD_ENABLED:
            await seed_from_channel(userbot.one)
    except Exception as e:
        LOGGER(__name__).warning(f"channel cache seed skipped: {e}")

    await Nand.start()

    try:
        await Nand.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("KeyaraMusic").warning(
            "Log group/channel me voice chat active nahi hai — bot chal raha hai, "
            "play ke liye VC on karo."
        )
    except:
        pass

    await Nand.decorators()

    LOGGER("KeyaraMusic").info(
        "Keyara Music Started Successfully.\n\nDon't forget to visit @KeyaraBots"
    )

    await idle()

    await app.stop()
    await userbot.stop()
    LOGGER("KeyaraMusic").info("Stopping Keyara Music Bot...🥺")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())


# ©️ Copyright Reserved - @NoxxOP  Nand Yaduwanshi

# ===========================================
# ©️ 2025 Nand Yaduwanshi (aka @NoxxOP)
# 🔗 GitHub : https://github.com/NoxxOP/KeyaraMusic
# 📢 Telegram Channel : https://t.me/ShrutiBots
# ===========================================


# ❤️ Love From ShrutiBots
