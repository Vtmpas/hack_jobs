from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings, QueryBundle, StorageContext, VectorStoreIndex
from llama_index.core.postprocessor import SentenceTransformerRerank

from _utils import create_document, HybridRetriever

import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().handlers = []
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

DATA = Path(__file__).parent.parent / 'backend' / "tmp_data"
Settings.embed_model = HuggingFaceEmbedding(
    model_name="intfloat/multilingual-e5-base",
    trust_remote_code=True
)

reranker = SentenceTransformerRerank(top_n=4, model="BAAI/bge-reranker-v2-m3")


def build_storage():
    dff = pd.read_excel(DATA / 'GeekBrains.xlsx').dropna(subset=['Программа обучения'])
    docs = [create_document(row) for _, row in dff.iterrows()]

    storage_context = StorageContext.from_defaults()
    storage_context.docstore.add_documents(docs)

    return docs, storage_context


def build_retriver(docs, strg):
    bm25_retriever = BM25Retriever.from_defaults(docstore=strg.docstore, similarity_top_k=2)

    index = VectorStoreIndex.from_documents(docs)
    vector_retriever = index.as_retriever(similarity_top_k=10)

    hybrid_retriever = HybridRetriever(vector_retriever, bm25_retriever)
    return hybrid_retriever


if __name__ == "__main__":
    documents, storage = build_storage()
    retiriver = build_retriver(documents, storage)

    prompt = """Рассвет 13 - команда экспертов и разработчиков в области управления данными и бизнес-аналитики.\
     Реализуем проекты для крупных федеральных компаний.

Приглашаем в команду Python-backend разработчика уровня middle.

Ожидания от кандидата:

опыт работы с Python;
опыт работы с фреймворками Django, FastAPI;
PostgresSQL / MS SQL-server,
понимание REST, SOAP;
опыт использования Alembic, Aiohttp, Lxml;
знание Docker.
Будет плюсом:

знание современных подходов к процессу тестирования.
Мы предлагаем:

Создавать продукты с нуля и решать неординарные задачи;
Работать с комфортом: гибкое начало рабочего дня, можно работать из офиса или удаленно; 5-дневная рабочая неделя;
Быть частью внутреннего IT-сообщества и регулярно обмениваться опытом;
Формировать культуру работы с данными в различных отраслях экономики;
Реализовать проекты, которые не стыдно показать в портфолио;
Оформление по ТК РФ;
Белая з/п (в соответствии с рынком);
Индивидуальный подход к заслугам и достижениям;
Индивидуальный план развития с регулярным пересмотром зп;
Участие в онлайн и оффлайн корпоративных мероприятиях интеллектуального и развлекательного характера.
Если вы хотите развиваться вместе с нами – откликайтесь на наши вакансии и присоединяйтесь к Рассвет 13!"""

    is_retrived = retiriver.retrieve(prompt)

    reranked_nodes = reranker.postprocess_nodes(
        is_retrived,
        query_bundle=QueryBundle(
            prompt
        ),
    )

    print(prompt)
    print("=" * 100)
    for node in reranked_nodes:
        print(node)
