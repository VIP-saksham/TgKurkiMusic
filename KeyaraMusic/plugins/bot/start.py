import asyncio
import random
import time

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from py_yt import VideosSearch
import config
from KeyaraMusic import app
from KeyaraMusic.misc import _boot_
from KeyaraMusic.utils.start_poster import render_start_poster
from KeyaraMusic.plugins.sudo.sudoers import sudoers_list
from KeyaraMusic.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from KeyaraMusic.utils import bot_sys_stats
from KeyaraMusic.utils.decorators.language import LanguageStart
from KeyaraMusic.utils.formatters import get_readable_time
from KeyaraMusic.utils.inline import help_pannel_page1, private_panel, start_panel
from config import BANNED_USERS
from strings import get_string


async def _post_start(**kw):
    """iOS start poster render karo (bina bheje) — caller hi photo+caption+buttons bhejta hai."""
    path = render_start_poster(**kw)
    return path or config.START_IMG_URL


_DICE_EMOJIS = ["🎲", "🎯", "🏀", "⚽", "🎳"]


async def _start_animation(message: Message):
    """/start par chhota dice animation — poster se pehle ki vibe."""
    try:
        return await message.reply_dice(emoji=random.choice(_DICE_EMOJIS))
    except Exception:
        return None


async def _end_start_animation(dice):
    if dice is None:
        return
    try:
        await asyncio.sleep(2.2)
        await dice.delete()
    except Exception:
        pass


@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)
    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]
        if name[0:4] == "help":
            keyboard = help_pannel_page1(_)
            try:
                return await message.reply_photo(
                    photo=config.START_IMG_URL,
                    caption=_["help_1"].format(config.SUPPORT_GROUP),
                    reply_markup=keyboard,
                )
            except:
                return await message.reply_photo(
                    photo=config.START_IMG_URL,
                    caption=_["help_1"].format(config.SUPPORT_GROUP),
                    reply_markup=keyboard,
                )
        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOG_GROUP_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )
            return
        if name[0:3] == "inf":
            m = await message.reply_text("🔎")
            query = (str(name)).replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]
            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )
            key = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text=_["S_B_8"], url=link),
                        InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_GROUP),
                    ],
                ]
            )
            await m.delete()
            try:
                await app.send_photo(
                    chat_id=message.chat.id,
                    photo=thumbnail,
                    caption=searched_text,
                    reply_markup=key,
                )
            except:
                await app.send_photo(
                    chat_id=message.chat.id,
                    photo=thumbnail,
                    caption=searched_text,
                    reply_markup=key,
                )
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOG_GROUP_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )
        if name == "start":
            dice = await _start_animation(message)
            out = private_panel(_)
            UP, CPU, RAM, DISK = await bot_sys_stats()
            photo = await _post_start(
                title=message.from_user.first_name,
                subtitle="Keyara Music me swagat hai",
                chips=[f"Uptime {UP}", f"RAM {RAM}", f"CPU {CPU}"],
                footer="Gaana chalane ke liye /play bhejo",
                seed=str(message.from_user.id),
            )
            await _end_start_animation(dice)
            try:
                await message.reply_photo(
                    photo=photo,
                    caption=_["start_2"].format(message.from_user.mention, app.mention, UP, DISK, CPU, RAM),
                    reply_markup=InlineKeyboardMarkup(out),
                )
            except:
                await message.reply_photo(
                    photo=config.START_IMG_URL,
                    caption=_["start_2"].format(message.from_user.mention, app.mention, UP, DISK, CPU, RAM),
                    reply_markup=InlineKeyboardMarkup(out),
                )
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOG_GROUP_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )
    else:
        dice = await _start_animation(message)
        out = private_panel(_)
        UP, CPU, RAM, DISK = await bot_sys_stats()
        photo = await _post_start(
            title=message.from_user.first_name,
            subtitle="Keyara Music me swagat hai",
            chips=[f"Uptime {UP}", f"RAM {RAM}", f"CPU {CPU}"],
            footer="Gaana chalane ke liye /play bhejo",
            seed=str(message.from_user.id),
        )
        await _end_start_animation(dice)
        try:
            await message.reply_photo(
                photo=photo,
                caption=_["start_2"].format(message.from_user.mention, app.mention, UP, DISK, CPU, RAM),
                reply_markup=InlineKeyboardMarkup(out),
            )
        except:
            await message.reply_photo(
                photo=config.START_IMG_URL,
                caption=_["start_2"].format(message.from_user.mention, app.mention, UP, DISK, CPU, RAM),
                reply_markup=InlineKeyboardMarkup(out),
            )
        if await is_on_off(2):
            return await app.send_message(
                chat_id=config.LOG_GROUP_ID,
                text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
            )


@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    photo = await _post_start(
        title=message.chat.title,
        subtitle="Keyara Music group me live hai",
        chips=[f"Uptime {get_readable_time(uptime)}"],
        footer="Ab yahan /play se gaana bajao",
        seed=f"grp{message.chat.id}",
    )
    try:
        await message.reply_photo(
            photo=photo,
            caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
            reply_markup=InlineKeyboardMarkup(out),
        )
    except:
        await message.reply_photo(
            photo=config.START_IMG_URL,
            caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
            reply_markup=InlineKeyboardMarkup(out),
        )
    return await add_served_chat(message.chat.id)


@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass
            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)
                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_GROUP,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)
                photo = await _post_start(
                    title=message.chat.title,
                    subtitle=f"{message.from_user.first_name} ne mujhe add kiya",
                    chips=["Swagat hai"],
                    footer="Ab yahan /play se gaana bajao",
                    seed=f"grp{message.chat.id}",
                )
                try:
                    await message.reply_photo(
                        photo=photo,
                        caption=_["start_3"].format(
                            message.from_user.first_name,
                            app.mention,
                            message.chat.title,
                            app.mention,
                        ),
                        reply_markup=InlineKeyboardMarkup(out),
                    )
                except:
                    await message.reply_photo(
                        photo=config.START_IMG_URL,
                        caption=_["start_3"].format(
                            message.from_user.first_name,
                            app.mention,
                            message.chat.title,
                            app.mention,
                        ),
                        reply_markup=InlineKeyboardMarkup(out),
                    )
                await add_served_chat(message.chat.id)
                await message.stop_propagation()
        except Exception as ex:
            print(ex)
