import logging
import sys

import pandas as pd
from llama_index.core import Settings, QueryBundle, StorageContext, VectorStoreIndex
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.retrievers.bm25 import BM25Retriever
from pathlib import Path

from src.backend.vacancies.services._utils import (create_document,
                                                   HybridRetriever,
                                                   post_process_metadata,
                                                   ProbaNodePostprocessor)
from src.backend.config import RecSysConfig


class SearchCourses:
    def __init__(self, config: RecSysConfig):
        self.DATA = Path(__file__).parents[2] / 'tmp_data' / 'GeekBrains.xlsx'
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        logging.getLogger().handlers = []
        logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

        Settings.embed_model = HuggingFaceEmbedding(
            model_name=config.vector_encoder,
            trust_remote_code=True
        )
        Settings.chunk_size = 16196
        Settings.chunk_overlap = 0

        self.reranker = SentenceTransformerRerank(top_n=3, model=config.reranker)

        self.documents, self.storage = self._build_storage()
        self.proba_estimator = ProbaNodePostprocessor()
        self.retiriver = self._build_retriver(self.documents, self.storage)

    def _build_storage(self, ):
        dff = pd.read_excel(self.DATA).dropna(subset=['Программа обучения'])
        docs = [create_document(row) for _, row in dff.iterrows()]

        storage_context = StorageContext.from_defaults()
        storage_context.docstore.add_documents(docs)

        return docs, storage_context

    def _build_retriver(self, docs, strg): # noqa
        bm25_retriever = BM25Retriever.from_defaults(docstore=strg.docstore, similarity_top_k=10)

        index = VectorStoreIndex.from_documents(docs)
        vector_retriever = index.as_retriever(similarity_top_k=10)

        hybrid_retriever = HybridRetriever(vector_retriever, bm25_retriever)
        return hybrid_retriever

    def get_vacancies_by_desc(self, desc: str):
        """
        Функция, возвращающая по текстовому описанию вакансии возможные курсы
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
        reranked_nodes = self.proba_estimator.postprocess_nodes(reranked_nodes)
        return [post_process_metadata(x) for x in reranked_nodes]
