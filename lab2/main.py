from elasticsearch import Elasticsearch
from config import ELASTIC_USER, ELASTIC_PASSWORD, INDEX
from typing import Optional, Generator
import typer
from datetime import datetime
from album_document import Album
from dataclasses import asdict
from uuid import uuid4, UUID
from enum import Enum
from queries import BoolQuery, QueryOption
from contextlib import contextmanager
from pathlib import Path

app = typer.Typer()


@contextmanager
def connect_es() -> Generator[Elasticsearch, None, None]:
    es = Elasticsearch("https://localhost:9200",  basic_auth=(ELASTIC_USER, ELASTIC_PASSWORD), verify_certs=True,
                   ca_certs="./http_ca.crt")
    try:
        yield es
    finally:
        es: Elasticsearch
        # es.transport.close()


@app.command()
def index_document(
    album_name: str = typer.Option(...),
    release_date: datetime = typer.Option(...),
    musicians: list[str] = typer.Option(...),
    box_office: int = typer.Option(...),
    text_path: Path = typer.Option(...),
) -> None:
    with connect_es() as es:
        res = []
        for path in ("description.txt", "critical_reception.txt", "additional_notes.txt"):
            with open(text_path / path, "r") as f:
                res.append(f.read())

        document = asdict(
            Album(album_name=album_name, release_date=release_date.date(), musicians=musicians, box_office=box_office,
                  description=res[0], critical_reception=res[1], additional_notes=res[2])
        )
        del document['_id']
        response = es.index(index=INDEX, id=str(uuid4()), document=document)
        print(response['result'])


@app.command()
def set_mapping(force_delete: bool = typer.Option(default=False)):
    analyzer = {
        "analysis": {
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords": "_english_"
                },
                "english_keywords": {
                    "type": "keyword_marker",
                    "keywords": ["example"]
                },
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "english_possessive_stemmer": {
                    "type": "stemmer",
                    "language": "possessive_english"
                }
            },
            "analyzer": {
                "custom_wikipedia_analyzer": {
                    "tokenizer": "standard",
                    "char_filter": [
                        "wikipedia_symbols"
                    ],
                    "filter": [
                        "lowercase",
                        "english_possessive_stemmer",
                        "english_stop",
                        "english_stemmer"
                    ]
                }
            },
            "char_filter": {
                "wikipedia_symbols": {
                    "type": "pattern_replace",
                    "pattern": "\[\d+\]",
                    "replacement": " "
                },
            }
        }
    }
    mapping = {
            "properties": {
                "album_name": {
                    "type": "keyword"
                },
                "musicians": {
                    "type": "keyword"
                },
                "box_office": {
                    "type": "integer"
                },
                "release_date": {
                    "type": "date"
                },
                "description": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "critical_reception": {
                    "type": "text",
                    "analyzer": "custom_wikipedia_analyzer"
                },
                "additional_notes": {
                    "type": "text",
                    "analyzer": "english"
                }
            }
        }
    with connect_es() as es:
        es: Elasticsearch
        if force_delete:
            es.options(ignore_status=[400, 404]).indices.delete(index=INDEX)
        es.indices.create(index=INDEX, mappings=mapping, settings=analyzer)


@app.command()
def search_by_album_name(album_name: str = typer.Argument(...)):
    with connect_es() as es:
        res = es.search(index=INDEX, query={"fuzzy": {"album_name": {"value": album_name}}})
        for hit in res['hits']['hits']:
            print(Album(**hit['_source'], _id=hit['_id']))


@app.command()
def delete(id: UUID):
    with connect_es() as es:
        response = es.delete(index=INDEX, id=str(id))
        print(response['result'])


class FilterOption(str, Enum):
    range = "range"
    term = "term"
    fuzzy = "fuzzy"


@app.command()
def add_fuzzy(option: QueryOption = typer.Argument(...), key: str = typer.Argument(...), value: str = typer.Argument(...), fuzziness: Optional[int] = typer.Argument(default=None, min=0, max=2)):
    with BoolQuery.load() as query:
        query.add_fuzziness(option, key, value, fuzziness)


@app.command()
def add_box_office_range(option: QueryOption = typer.Argument(...), gte: float = typer.Argument(default=None), lte: float = typer.Argument(default=None),):
    with BoolQuery.load() as query:
        if gte is None and lte is None:
            print("WARNING: both gte and lte is not set, skipping range addition")
            pass
        query.add_range(option, "box_office", gte, lte)


@app.command()
def add_release_date_range(option: QueryOption = typer.Argument(...), gte: datetime = typer.Argument(default=None), lte: datetime = typer.Argument(default=None),):
    with BoolQuery.load() as query:
        if gte is None and lte is None:
            print("WARNING: both gte and lte is not set, skipping range addition")
            pass
        query.add_range(option, "release_date", gte.date(), lte.date())


@app.command()
def add_term(
        option: QueryOption = typer.Argument(...), key: str = typer.Argument(...), value: str = typer.Argument(...)
):
    with BoolQuery.load() as query:
        query: BoolQuery
        query.add_term(option, key, value)

@app.command()
def add_match(
        option: QueryOption = typer.Argument(...), key: str = typer.Argument(...), value: str = typer.Argument(...)
):
    with BoolQuery.load() as query:
        query: BoolQuery
        query.add_match(option, key, value)

@app.command()
def search(display_texts: bool = typer.Option(default=False)):
    with BoolQuery.load() as query:
        query: BoolQuery
        search_query = query.to_dict()
        with connect_es() as es:
            res = es.search(index=INDEX, query=search_query)
            for hit in res['hits']['hits']:
                album = Album(**hit['_source'], _id=hit['_id'], _score=hit['_score'])
                if not display_texts:
                    album.description = ""
                    album.additional_notes = ""
                    album.critical_reception = ""
                print(album)


@app.command()
def reset_query():
    BoolQuery.reset_query()


if __name__ == "__main__":
    app()
