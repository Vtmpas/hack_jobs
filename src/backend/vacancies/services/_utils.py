from typing import List, Optional

from math import exp
import pandas as pd

from llama_index.core import Document, QueryBundle
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore


class ProbaNodePostprocessor(BaseNodePostprocessor):
    def _postprocess_nodes(
            self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle]
    ) -> List[NodeWithScore]:
        # First, compute the sum of exponentials of the scores
        sum_exp_scores = sum(exp(node.score) for node in nodes)

        # Apply the softmax function to each score
        for node in nodes:
            node.score = exp(node.score) / sum_exp_scores

        return nodes


class HybridRetriever(BaseRetriever):
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        super().__init__()

    def _retrieve(self, query, **kwargs):
        bm25_nodes = self.bm25_retriever.retrieve(query, **kwargs)
        vector_nodes = self.vector_retriever.retrieve(query, **kwargs)

        # combine the two lists of nodes
        all_nodes = []
        node_ids = set()
        for n in bm25_nodes + vector_nodes:
            if n.node.metadata['spec_idx'] not in node_ids:
                all_nodes.append(n)
                node_ids.add(n.node.metadata['spec_idx'])
        return all_nodes


def preprocess_row(row: pd.Series) -> pd.Series:
    full_text = ''
    row = row[:]
    for k, v in row.to_dict().items():
        if k == 'Ссылка на курс':
            continue
        full_text += f'{k}: {v}\n'

    row['full_text'] = full_text
    return row


def create_document(row: pd.Series = None,
                    text_col: str = 'full_text',
                    exclude_cols: List[str] = None
                    ) -> Document:
    if exclude_cols is None:
        exclude_cols = ['Ссылка на курс', 'spec_idx']

    row = preprocess_row(row)

    row['spec_idx'] = hash(row['Название профессии'] + str(row['Период обучения']) + row['Стек технологий'])

    document = Document(
        text=row[text_col],
        metadata=row.loc[['Название профессии',
                          'Стек технологий',
                          'Ссылка на курс', 'Описание курса',
                          'Период обучения', 'spec_idx']].to_dict(),
        excluded_llm_metadata_keys=exclude_cols,
        metadata_seperator="::",
        metadata_template="{key}=>{value}",
        text_template="Metadata: {metadata_str}\n-----\nContent: {content}",
    )
    return document


def extract_names(json_obj, field_name):
    try:
        return [val['name'] for val in json_obj[field_name]]
    except Exception as e:
        print(e)
        return []


def post_process_metadata(node):
    result = {}
    for k, v in node.node.metadata.items():
        if k in ['Ссылка на курс', 'Название профессии', 'Описание курса']:
            result[str(k)] = str(v)

    result['Match probability'] = str(node.score * 100) + '%'
    return result
