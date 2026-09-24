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


import os
from typing import List

import yaml

languages = {}
languages_present = {}

def _normalize_ui_text(value):
    if isinstance(value, str):
        return value.replace(
            "https://t.me/BlushMusicbot?start=help",
            "https://t.me/KeyaraMusicBot?start=help",
        )
    if isinstance(value, dict):
        return {key: _normalize_ui_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_ui_text(item) for item in value]
    return value


def get_string(lang: str):
    return languages[lang]


for filename in os.listdir(r"./strings/langs/"):
    if "en" not in languages:
        languages["en"] = _normalize_ui_text(yaml.safe_load(
            open(r"./strings/langs/en.yml", encoding="utf8")
        ))
        languages_present["en"] = languages["en"]["name"]
    if filename.endswith(".yml"):
        language_name = filename[:-4]
        if language_name == "en":
            continue
        languages[language_name] = _normalize_ui_text(yaml.safe_load(
            open(r"./strings/langs/" + filename, encoding="utf8")
        ))
        for item in languages["en"]:
            if item not in languages[language_name]:
                languages[language_name][item] = languages["en"][item]
    try:
        languages_present[language_name] = languages[language_name]["name"]
    except:
        print("There is some issue with the language file inside bot.")
        exit()


# ©️ Copyright Reserved - @NoxxOP  Nand Yaduwanshi

# ===========================================
# ©️ 2025 Nand Yaduwanshi (aka @NoxxOP)
# 🔗 GitHub : https://github.com/NoxxOP/ShrutiMusic
# 📢 Telegram Channel : https://t.me/ShrutiBots
# ===========================================


# ❤️ Love From ShrutiBots 
