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

app = typer.Typer()


@contextmanager
def connect_es() -> Generator[Elasticsearch, None, None]:
    es = Elasticsearch("https://localhost:9200",  basic_auth=(ELASTIC_USER, ELASTIC_PASSWORD), verify_certs=True,
                   ca_certs="./http_ca.crt")
    try:
        yield es
    finally:
        es: Elasticsearch
        es.transport.close()


@app.command()
def index_document(
    album_name: str = typer.Option(...),
    release_date: datetime = typer.Option(...),
    musicians: list[str] = typer.Option(...),
    box_office: int = typer.Option(...)
) -> None:
    with connect_es() as es:
        document = asdict(
            Album(album_name=album_name, release_date=release_date.date(), musicians=musicians, box_office=box_office)
        )
        del document['_id']
        response = es.index(index=INDEX, id=str(uuid4()), document=document)
        print(response['result'])


@app.command()
def set_mapping(force_delete: bool = typer.Option(default=False)):
    mapping = {
        "mappings": {
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
                }
            }
        }
    }
    with connect_es() as es:
        if force_delete:
            es.options(ignore_status=[400, 404]).indices.delete(index=INDEX)
        es.indices.create(index=INDEX, body=mapping)


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
def search():
    with BoolQuery.load() as query:
        query: BoolQuery
        search_query = query.to_dict()
        with connect_es() as es:
            res = es.search(index=INDEX, query=search_query)
            for hit in res['hits']['hits']:
                print(Album(**hit['_source'], _id=hit['_id']))


@app.command()
def reset_query():
    BoolQuery.reset_query()


if __name__ == "__main__":
    app()
