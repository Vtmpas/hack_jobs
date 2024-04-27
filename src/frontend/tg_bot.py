import nest_asyncio
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup
import sys
from pathlib import Path
import asyncio

SCRIPT_DIR = os.path.dirname(Path(__file__).parent)

sys.path.append(os.path.dirname(SCRIPT_DIR))
from src.backend import search

nest_asyncio.apply()
sys.path.append(str(Path(__file__).parent))

TOKEN = os.environ.get('TG_TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher()

documents, storage = search.build_storage()
retiriver = search.build_retriver(documents, storage)


@dp.message(Command('start'))
async def process_start_command(message: types.Message):
    await message.reply(
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
            async with session.get(api_url) as resp:
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
        return {"error": str(e)}


def hh_link_filter(url: str) -> bool:
    return "hh.ru" in url


@dp.message()  # lambda msg: hh_link_filter(msg.text))
async def echo_message(msg: types.Message):
    url = msg.text.strip()
    parseresult = urlparse(url)
    vacancy_id = Path(parseresult.path).name
    print(0)
    vacancy_data = await get_vacancy_data(vacancy_id)

    description = vacancy_data["description"]

    print(1)
    is_retrived = retiriver.retrieve(description)
    print(2)

    reranked_nodes = search.reranker.postprocess_nodes(
        is_retrived,
        query_bundle=search.QueryBundle(
            description
        ),
    )
    print(3)

    for i in range(4):
        node = reranked_nodes[i]
        answer = ""
        for key, value in node.metadata.items():
            answer += f"{key}: {value}\n"

        answer += "\n\n" + node.text
        await bot.send_message(msg.from_user.id, answer[:4000])


#@dp.message(lambda msg: not hh_link_filter(msg.text)) # noqa
#async def echo_message(msg: types.Message): # noqa
#    await bot.send_message(msg.from_user.id, "Нужно кинуть ссылку на hh.ru")


async def main():
    await dp.start_polling(bot)


if True or (__name__ == "__main__"):
    print("Here")
    asyncio.run(main())
