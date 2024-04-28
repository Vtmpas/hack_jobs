import os
import nest_asyncio
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup
from requests import post
import sys
from pathlib import Path
import asyncio

import pandas as pd

from aiogram import F
import re

SCRIPT_DIR = os.path.dirname(Path(__file__).parent)

sys.path.append(os.path.dirname(SCRIPT_DIR))
from src.backend._tesseract import pdf_parser

nest_asyncio.apply()
sys.path.append(str(Path(__file__).parent))

TOKEN = os.environ['TG_TOKEN']

bot = Bot(token=TOKEN)
dp = Dispatcher()

URL = 'http://0.0.0.0:8000/vacancies/recommend'


button_like = types.InlineKeyboardButton(text="👍", callback_data="send_like")
button_dislike = types.InlineKeyboardButton(text="👎", callback_data="send_dislike")
kb = [
  [
    button_like,
    button_dislike
  ]
]
keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb, one_time_keyboard=True)

markup_final = pd.read_excel("GeekBrains_fin.xlsx")

def prettify_recommendations(data):
    message = "Вот Ваши метчи:\n"
    for item in data:
        message += f"\n🎓 Профессия: {item['Название профессии']}\n"
        message += f"🔗 [Course Link]({item['Ссылка на курс']})\n"
        message += f"📄 Описание: {item['Описание курса']}\n"
        message += f"🎯 Шанс метча: {item['Match probability']}\n"
    return message.strip()

def prettify_recommendation(dict_obj):
    message = ""
    message += f"\n🎓 Профессия: {dict_obj['Название профессии']}\n"
    message += f"🔗 [Course Link]({dict_obj['Ссылка на курс']})\n"
    message += f"📄 Описание: {dict_obj['Описание курса']}\n"
    message += f"🎯 Шанс метча: {dict_obj['Match probability']}\n"
    return message.strip()

@dp.callback_query(F.data == "send_like")
async def reply_on_like(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, 'Рады помочь!')
    await callback.message.delete_reply_markup()

@dp.callback_query(F.data == "send_dislike")
async def reply_on_dislike(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, 'Возможно вам будет интересен курс по ИИ')
    await callback.message.delete_reply_markup()


@dp.message(Command('start'))
async def process_start_command(message: types.Message):
    start_message = (
        "Привет! Я бот, который поможет тебе подобрать курсы от GeekBrains, "
        "наиболее подходящие для той вакансии, которую ты рассматриваешь. 🎓\n\n"
        "Ты можешь отправить мне ссылку на интересующую тебя вакансию с сайта hh.ru, "
        "PDF-файл с описанием вакансии или просто текстовое описание должности. "
        "На основе предоставленной информации я предложу курсы, которые помогут тебе стать идеальным кандидатом для этой работы. 💼"
    )

    await message.answer(start_message)


def extract_names(json_obj, field_name):
    try:
        return [val['name'] for val in json_obj[field_name]]
    except Exception as e:
        print(e)
        return []


async def get_vacancy_data(vacancy_id):
    api_url = f'https://api.hh.ru/vacancies/{vacancy_id}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, ssl=False) as resp:
                x = await resp.json()

        soup = BeautifulSoup(x['description'], 'html.parser')
        desc_text = soup.get_text()

        return {
            "id": vacancy_id,
            "name": x['name'],
            "experience": extract_names(x, "experience"),
            "description": desc_text,
            "key_skills": extract_names(x, "key_skills"),
            "professional_roles": extract_names(x, "professional_roles"),
            "employer": x['employer']['name']
        }

    except Exception as e:
        print({"error": str(e)})
        return {"error": str(e)}


def hh_link_filter(url: str) -> bool:
    return "hh.ru" in url


def _check_is_url(request: str):
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  #domain...
            r'localhost|'  #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return re.match(regex, request) is not None

async def send_recommendations(msg: types.Message, vacancy_data, description, recommendations_raw):
    await bot.send_message(msg.from_user.id, "Вот Ваши метчи:")
    for rec_item in recommendations_raw:
        await bot.send_message(msg.from_user.id, prettify_recommendation(rec_item))

        skills_from_vac = vacancy_data['key_skills']
        course_url = rec_item['Ссылка на курс']
        all_skills_str = markup_final[markup_final['Ссылка на курс'] == course_url]['Стек технологий'].values[0].lower()
        matched_skills = []
        unmatched_skills = []
        for vac_skill in skills_from_vac:
            if all_skills_str.find(vac_skill.lower()) != -1 or description.lower().find(vac_skill.lower()) != -1:
                matched_skills.append(vac_skill)
            else:
                unmatched_skills.append(vac_skill)
        matched_skills = sorted(matched_skills)
        unmatched_skills = sorted(unmatched_skills)

        if len(matched_skills) > 0:
            if len(matched_skills) / len(skills_from_vac) > 0.5:
                base_info = "Курс покрывает большинство требований вакансии\n\n"
            else:
                base_info = "Курс покрывает только часть требований вакансии\n\n"
            coverage_info = base_info + "✅ " + ",".join(matched_skills)
            if len(matched_skills) > 0:
                coverage_info += "\n\n" + "❌ " + ",".join(unmatched_skills)
                await bot.send_message(msg.from_user.id, coverage_info)


@dp.message() # lambda msg: hh_link_filter(msg.text))
async def echo_message(msg: types.Message):
    print(dir(msg))
    print(msg.document)
    if msg.document is not None:

        file_info = await bot.get_file(msg.document.file_id)
        print(file_info)
        downloaded_file = await bot.download_file(file_info.file_path)
        try:
            with open('vacancy.pdf', 'wb') as new_file:
                new_file.write(downloaded_file.getvalue())
            description = pdf_parser("vacancy.pdf")
            await bot.send_message(msg.from_user.id, 'Уже изучил описание вакансии. Еще совсем немного ...')
            recommendations_raw = eval(post(url=URL, json={'description':description}).text)['recommendations']
            await send_recommendations(msg, vacancy_data, description, recommendations_raw)
            # await bot.send_message(msg.from_user.id, prettify_recommendations(eval(post(url=URL,
            #                                               json={'description':description}).text)['recommendations'])
            #                        )
        except Exception as e:
            await bot.send_message(msg.from_user.id, 'Рекомендуем курс по внедрению ИИ')


    elif _check_is_url(msg.text.strip()):

        url = msg.text.strip()
        if not hh_link_filter(url):
            await bot.send_message(msg.from_user.id, 'Обрабатываем только ссылки на hh')
        else:
            try:
                parseresult = urlparse(url)
                vacancy_id = Path(parseresult.path).name
                vacancy_data = await get_vacancy_data(vacancy_id)
                description = vacancy_data["description"]
                await bot.send_message(msg.from_user.id, 'Уже изучил описание вакансии. Еще совсем немного ...')
                recommendations_raw = eval(post(url=URL, json={'description':description}).text)['recommendations']
                await send_recommendations(msg, vacancy_data, description, recommendations_raw)

            except Exception as e:
                await bot.send_message(msg.from_user.id, 'Рекомендуем курс по внедрению ИИ')


    else:
        description = msg.text.strip()
        await bot.send_message(msg.from_user.id, 'Уже изучил описание вакансии. Еще совсем немного ...')
        recommendations_raw = eval(post(url=URL, json={'description':description}).text)['recommendations']
        await send_recommendations(msg, vacancy_data, description, recommendations_raw)
        # await bot.send_message(msg.from_user.id, prettify_recommendations(eval(post(url=URL,
        #                                               json={'description':description}
        #                                               ).text)['recommendations'])
        #                        )
    await bot.send_message(msg.from_user.id, "Оцените рекомендации", reply_markup=keyboard)


@dp.message(lambda msg: not hh_link_filter(msg.text)) # noqa
async def echo_message(msg: types.Message): # noqa
   await bot.send_message(msg.from_user.id, "Нужно кинуть ссылку на hh.ru")


async def main():
    await dp.start_polling(bot)


if True or (__name__ == "__main__"):
    print("Here")
    asyncio.run(main())
