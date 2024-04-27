import nest_asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup
import sys
from pathlib import Path
import asyncio

from aiogram import F
import re

SCRIPT_DIR = os.path.dirname(Path(__file__).parent)

sys.path.append(os.path.dirname(SCRIPT_DIR))
from src.backend.vacancies.services import analyzer
from src.backend._tesseract import pdf_parser

nest_asyncio.apply()
sys.path.append(str(Path(__file__).parent))

TOKEN = os.environ['TG_TOKEN']

bot = Bot(token=TOKEN)
dp = Dispatcher()

# search_courses = SearchCourses()
# documents = search_courses.documents
# storage = search_courses.storage
# retiriver = search_courses._build_retriver(documents, storage)

button_like = types.InlineKeyboardButton(text="👍", callback_data="send_like")
button_dislike = types.InlineKeyboardButton(text="👎", callback_data="send_dislike")
kb = [
  [
    button_like,
    button_dislike
  ]
]
keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb, one_time_keyboard=True)


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

    await message.answer(
        "Привет! Это бот для подбора курсов под вакансию. Отправь ссылку на вакансию на hh.ru и бот подберёт тебе \
         подходящие курсы.")


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
            await bot.send_message(msg.from_user.id, description[:2000])
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
                await bot.send_message(msg.from_user.id, description)
            except Exception as e:
                await bot.send_message(msg.from_user.id, 'Рекомендуем курс по внедрению ИИ')


    else:
        description = msg.text.strip()
        await bot.send_message(msg.from_user.id, description)
    await bot.send_message(msg.from_user.id, "Оцените рекомендации", reply_markup=keyboard)


# @dp.message()  # lambda msg: hh_link_filter(msg.text))
# async def echo_message(msg: types.Message):
#     url = msg.text.strip()
#     parseresult = urlparse(url)
#     vacancy_id = Path(parseresult.path).name
#     print(0)
#     vacancy_data = await get_vacancy_data(vacancy_id)

#     await bot.send_message(msg.from_user.id, str(vacancy_data))
#     await bot.send_message(msg.from_user.id, "Оцените рекомендации", reply_markup=keyboard)

    # description = vacancy_data["description"]

    # print(1)
    # is_retrived = retiriver.retrieve(description)
    # print(2)

    # reranked_nodes = search_courses.reranker.postprocess_nodes(
    #     is_retrived,
    #     query_bundle=search.QueryBundle(
    #         description
    #     ),
    # )
    # print(3)

    # for i in range(4):
    #     node = reranked_nodes[i]
    #     answer = ""
    #     for key, value in node.metadata.items():
    #         answer += f"{key}: {value}\n"

    #     answer += "\n\n" + node.text
    #     await bot.send_message(msg.from_user.id, answer[:4000])



@dp.message(lambda msg: not hh_link_filter(msg.text)) # noqa
async def echo_message(msg: types.Message): # noqa
   await bot.send_message(msg.from_user.id, "Нужно кинуть ссылку на hh.ru")


async def main():
    await dp.start_polling(bot)


if True or (__name__ == "__main__"):
    print("Here")
    asyncio.run(main())
