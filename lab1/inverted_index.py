from typing import Generator
from dataclasses import dataclass, asdict, field
import json
from contextlib import contextmanager
import os
from pathlib import Path
from collections import defaultdict
import logging
import re


INDEX_TERMS_PATH = "index_terms.json"


@dataclass()
class InvertedIndex:
    index_terms: defaultdict[str, dict[str, list[str]]] = field(default_factory=dict)
    new_index_terms_allowed: bool = True

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
                self.index_document(path.name, document)

    def index_document(self, name: str, document: str):
        words = set(document.replace(",", "").replace(".", "").replace("\n", " ").lower().split(" "))
        for word in words:
            indexed_documents = self.index_terms["index_terms"].get(word, None)
            if indexed_documents is not None and name not in indexed_documents:
                indexed_documents.append(name)

    def _construct_words(self, normal_conjunctive: str) -> list[set[str]]:
        indexes = [m.start() for m in re.finditer('&', normal_conjunctive)]
        indexes.append(len(normal_conjunctive) - 1)
        last_index = -1
        search_by_words: list[set] = []
        for index in indexes:
            disjunctive = normal_conjunctive[last_index + 1:index + 1].replace("&", "")
            terms_between = [m.start() for m in re.finditer('\"', disjunctive)]
            assert len(terms_between) % 2 == 0
            words = set()
            for position, index_start in enumerate(terms_between):
                if position % 2 == 1:
                    continue
                words.add(disjunctive[index_start + 1:terms_between[position + 1]])
            last_index = index
            search_by_words.append(words)
        return search_by_words

    def search(self, normal_conjunctive: str):
        words_collection = self._construct_words(normal_conjunctive)
        result: set | None = None
        for words in words_collection:
            disjunction = set()
            for word in words:
                indexed = self.index_terms["index_terms"].get(word, None)
                if indexed is not None:
                    disjunction.update(indexed)
            print(disjunction)
            if result is None:
                result = disjunction
            else:
                result = result.intersection(disjunction)
        return result

    def save(self) -> None:
        with open(INDEX_TERMS_PATH, "w") as f:
            json.dump(asdict(self), f, default=str, indent=4)

    @classmethod
    @contextmanager
    def load(cls) -> Generator['InvertedIndex', None, None]:
        try:
            with open(INDEX_TERMS_PATH, "r") as f:
                index_terms = json.load(f)
                query = cls(**index_terms)
        except (FileNotFoundError, json.JSONDecodeError):
            query = cls()
        try:
            yield query
        finally:
            query.save()

    @classmethod
    def reset_index_terms(cls) -> None:
        os.unlink(INDEX_TERMS_PATH)

