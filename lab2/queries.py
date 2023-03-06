from typing import Any, Optional, Generator, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
from contextlib import contextmanager
import os
from datetime import date


QUERY_PATH = "query.json"

ElasticQueryOperator = dict[str, Any]


class QueryOption(str, Enum):
    must = "must"
    must_not = "must_not"
    should = "should"
    filter = "filter"


@dataclass()
class BoolQuery:
    must_not: list[Optional[ElasticQueryOperator]] = field(default_factory=list)
    must: list[Optional[ElasticQueryOperator]] = field(default_factory=list)
    should: list[Optional[ElasticQueryOperator]] = field(default_factory=list)
    filter: list[Optional[ElasticQueryOperator]] = field(default_factory=list)


    def _get_option(self, option: QueryOption) -> Optional[list]:
        options = {QueryOption.must: self.must, QueryOption.must_not: self.must_not, QueryOption.should: self.should,
                   QueryOption.filter: self.filter}
        return options.get(option)

    def to_dict(self) -> ElasticQueryOperator:
        es_query: dict[str, list[ElasticQueryOperator]] = {
            "must_not": [op for op in self.must_not if op is not None],
            "must": [op for op in self.must if op is not None],
            "should": [op for op in self.should if op is not None],
            "filter": [op for op in self.filter if op is not None],
        }

        filtered: ElasticQueryOperator = {key: value for key, value in es_query.items() if len(value) > 0}
        return {"bool": filtered}

    def add_fuzziness(self, option: QueryOption, key: str, value: str, fuzziness: Optional[int] = None):
        query_value = self._get_option(option)
        if fuzziness is None:
            fuzziness = "AUTO"
        query_value.append({"match": {key: {"query": value, "fuzziness": fuzziness}}})

    def add_range(self, option: QueryOption, key: str, gte: Optional[Union[float, date]], lte: Optional[Union[float, date]]):
        query_value = self._get_option(option)
        query_value.append({"range": {key: {"gte": gte, "lte": lte}}})

    def add_term(self, option: QueryOption, key: str, value: str):
        query_value = self._get_option(option)
        query_value.append({"term": {key: value}})

    def add_match(self, option: QueryOption, key: str, value: str):
        query_value = self._get_option(option)
        query_value.append({"match": {key: value}})

    def save(self) -> None:
        with open(QUERY_PATH, "w") as f:
            json.dump(asdict(self), f, default=str, indent=4)

    @classmethod
    @contextmanager
    def load(cls) -> Generator['BoolQuery', None, None]:
        try:
            with open(QUERY_PATH, "r") as f:
                data = json.load(f)
                query = cls(**data)
        except FileNotFoundError:
            query = cls()
        try:
            yield query
        finally:
            query.save()

    @classmethod
    def reset_query(cls) -> None:
        os.unlink(QUERY_PATH)