from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings, QueryBundle, StorageContext, VectorStoreIndex
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.schema import MetadataMode
from llama_index.retrievers.bm25 import BM25Retriever

from ._utils import create_document, HybridRetriever

import logging
import sys
from pathlib import Path

import pandas as pd
import re
from urllib.parse import urlparse

class SearchCourses:
    def __init__(self,):

        self.DATA = "tmp_data"
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        logging.getLogger().handlers = []
        logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))
        
        
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="intfloat/multilingual-e5-base",
            trust_remote_code=True
        )
        Settings.chunk_size = 16196
        Settings.chunk_overlap = 0

        self.reranker = SentenceTransformerRerank(top_n=5, model="BAAI/bge-reranker-v2-m3")

        self.documents, self.storage = self._build_storage()
        self.retiriver = self._build_retriver(self.documents, self.storage)

    
    def _build_storage(self,):
        dff = pd.read_excel(self.DATA + '/GeekBrains.xlsx').dropna(subset=['Программа обучения'])
        docs = [create_document(row) for _, row in dff.iterrows()]
    
        storage_context = StorageContext.from_defaults()
        storage_context.docstore.add_documents(docs)
    
        return docs, storage_context


    def _build_retriver(self, docs, strg):
        bm25_retriever = BM25Retriever.from_defaults(docstore=strg.docstore, similarity_top_k=10)
    
        index = VectorStoreIndex.from_documents(docs)
        vector_retriever = index.as_retriever(similarity_top_k=10)
    
        hybrid_retriever = HybridRetriever(vector_retriever, bm25_retriever)
        return hybrid_retriever


    ## можно добавить возможные типы входных данных: pdf-файл с описанием вакансии/картинка с описанием
    def get_vacancies_by_desc(self, desc: str):
        """
        Функция возвращаюшая по текстовому описанию вакансии возможные курсы
        -------------------------------------
        params:
        desc: описание вакансии
        rtype: str
        -------------------------------------
        return:
        vacancy_info : {аттрибут: значение}. Ключи:
            name - название вакансии
            description - описание
            key_skills - ключевые скиллы
        rtype: dict
        """
       
        
        prompt = f"{desc}"
    
        is_retrived = self.retiriver.retrieve(prompt)
    
        reranked_nodes = self.reranker.postprocess_nodes(
            is_retrived,
            query_bundle=QueryBundle(
                prompt
            ),
        )

        # response = {}
        
    
        print(prompt)
        print("=" * 100)
        for node in reranked_nodes:
            print(node)
    
        print("=" * 100)
        print(reranked_nodes[0].get_content(metadata_mode=MetadataMode.EMBED))


    def _check_is_url(self, request: str):
        regex = re.compile(
                r'^(?:http|ftp)s?://' # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                r'localhost|' #localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
                r'(?::\d+)?' # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return re.match(regex, request) is not None
         

    def _vacancy_info_by_url(self, url: str):
        """
        Функция возвращаюшая описание вакансии по ссылке на вакансию с hh.ru
        -------------------------------------
        params:
        url: ссылка с hh.ru
        rtype: str
        -------------------------------------
        return:
        vacancy_info : {аттрибут: значение}. Ключи:
            name - название вакансии
            description - описание
            key_skills - ключевые скиллы
        rtype: dict
        """
        vacancy_description = ""
        if url.startswith('www.') or url.startswith('hh.ru'):
            url = 'http://' + url

        if not self._check_is_url(url):
             raise ValueError("not correct url")

        url_parse = urlparse(url)
        vacancy_id = url_parse.path.split('/')[-1]
            
        try:
            x = requests.get(f'https://api.hh.ru/vacancies/{vacancy_id}').json()
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
            
        except:
            return {
                "id": vacancy_id,
                "name": None,
                "experience": None,
                "description": None,
                "key_skills": None,
                "professional_roles": None,
                "employer": None
            }


    ## можно добавить возможные типы входных данных: pdf-файл с описанием вакансии/картинка с описанием
    def get_vacancies_by_url(self, url: str):
        """
        Функция возвращаюшая по текстовому описанию вакансии возможные курсы
        -------------------------------------
        params:
        request: описание вакансии
        rtype: str
        -------------------------------------
        return:
        vacancy_info : {аттрибут: значение}. Ключи:
            name - название вакансии
            description - описание
            key_skills - ключевые скиллы
        rtype: dict
        """
        vacancy_info = self._vacancy_info_by_url(url)
        vacancy_description = vacancy_info["description"]
        self.get_vacancies_by_desc(vacancy_description)



if __name__ == "__main__":
    search = SearchCourses()

    # 'https://hh.ru/vacancy/96428016'
    search.get_vacancies_by_url('https://hh.ru/vacancy/96176670?query=%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B8%D1%81%D1%82+1C&hhtmFrom=vacancy_search_list')
                                

    vacancy_desc = """Рассвет 13 - команда экспертов и разработчиков в области управления данными и бизнес-аналитики.\
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

    search.get_vacancies_by_desc(vacancy_desc)
