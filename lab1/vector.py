from typing import Generator
from dataclasses import dataclass, asdict, field
import json
from contextlib import contextmanager
from pathlib import Path
from collections import defaultdict
import logging
from math import log
import re

VECTOR_INDEX_TERMS_PATH = "vector_index_terms.json"

COSINE_SIMILIARITY_THRESHOLD = -1

@dataclass
class DocumentTermData:
    occurrences: int = 0
    tf: float = 0
    idf: float = 0
    tf_idf: float = 0


@dataclass
class VectorIndex:
    index_terms: defaultdict[str, dict[str, list[str]]] = field(default_factory=dict)
    new_index_terms_allowed: bool = True
    indexed_documents: dict[str, dict[str, DocumentTermData]] = field(default_factory=dict)

    def replace_index_terms(self, path: Path) -> None:
        if not self.new_index_terms_allowed:
            logging.warning("Adding index terms after initialisation is not allowed.")
            return
        with open(path, "r") as f:
            index_terms = json.load(f)
            self.index_terms["index_terms"] = {}
            for key in index_terms["index_terms"].keys():
                self.index_terms["index_terms"][key] = []
            self.new_index_terms_allowed = False

    def index_text_corpus(self, dir_path: Path):
        pathlist = Path(dir_path).glob('*')
        for path in pathlist:
            with open(path, "r") as f:
                document = "".join(f.readlines())
                self._index_document(path.name, document)
        self._calculate_tf()
        self._calculate_idf()
        self._calculate_tf_idf()

    def _calculate_tf(self):
        for name, value in self.indexed_documents.items():
            overall_terms_in_document = sum(item.occurrences for item in value.values())
            for term, info in value.items():
                info.tf = self.__tf_formula(info.occurrences, overall_terms_in_document)

    def _calculate_idf(self):
        overall_documents = len(self.indexed_documents)
        for name, value in self.indexed_documents.items():
            for term, info in value.items():
                documents_term_in = sum(1 for db_document_terms in self.indexed_documents.values() if term in db_document_terms)
                info.idf = self.__idf_formula(overall_documents, documents_term_in)

    def _calculate_tf_idf(self):
        for name, value in self.indexed_documents.items():
            for info in value.values():
                info.tf_idf = info.tf * info.idf

    @classmethod
    def __tf_formula(cls, term_occurrences_in_document: int, overall_terms_occurrences_in_document: int) -> float:
        return term_occurrences_in_document / overall_terms_occurrences_in_document

    @classmethod
    def __idf_formula(cls, overall_documents: int, term_is_in_documents: int) -> float:
        return log(overall_documents / term_is_in_documents)

    def _index_document(self, name: str, document: str):
        words = list(document.replace(",", "").replace(".", "").replace("\n", " ").lower().split(" "))
        self.indexed_documents[name] = {}

        for word in words:
            if word in self.index_terms["index_terms"]:
                document_data = self.indexed_documents[name].get(word, DocumentTermData())
                document_data.occurrences += 1
                self.indexed_documents[name][word] = document_data

    @classmethod
    def _extract_terms(self, query: str) -> list[str]:
        terms_between = [m.start() for m in re.finditer('\"', query)]
        words = []
        for position, index_start in enumerate(terms_between):
            if position % 2 == 1:
                continue
            words.append(query[index_start + 1:terms_between[position + 1]])
        return words

    def _calculate_query_weight(self, query: list[str]) -> dict[str, float]:
        result = {}
        for word in query:
            if word in self.index_terms["index_terms"]:
                result[word] = 1.0
            else:
                continue
        return result

    def _cosine_similarity(self, query: list[str]):
        query_weight = self._calculate_query_weight(query)
        sum_query_normilized = sum(value ** 2 for value in query_weight.values()) ** (1 / 2)
        result = []
        for document_name, value in self.indexed_documents.items():
            sum_indexed_terms = 0
            sum_upper = 0
            for term, term_weight in query_weight.items():
                documnet_term_data = DocumentTermData(**value.get(term, {}))

                sum_upper += documnet_term_data.tf_idf * term_weight
                sum_indexed_terms += documnet_term_data.tf_idf ** 2
            sum_indexed_terms **= (1 / 2)
            if sum_indexed_terms == 0:
                continue
            similiarity = sum_upper / (sum_indexed_terms * sum_query_normilized)
            if similiarity > COSINE_SIMILIARITY_THRESHOLD:
                result.append((document_name, similiarity))
        return sorted(result, key=lambda x: x[1], reverse=True)

    def search(self, query: str) -> list[tuple[str, float]]:
        words = self._extract_terms(query)
        result = self._cosine_similarity(words)
        return result

    def save(self) -> None:
        with open(VECTOR_INDEX_TERMS_PATH, "w") as f:
            json.dump(asdict(self), f, default=str, indent=4)

    @classmethod
    @contextmanager
    def load(cls) -> Generator['VectorIndex', None, None]:
        try:
            with open(VECTOR_INDEX_TERMS_PATH, "r") as f:
                index_terms = json.load(f)
                query = cls(**index_terms)
        except (FileNotFoundError, json.JSONDecodeError):
            query = cls()
        try:
            yield query
        finally:
            query.save()