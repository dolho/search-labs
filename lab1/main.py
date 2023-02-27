import typer
from inverted_index import InvertedIndex
from vector import VectorIndex
from pathlib import Path

app = typer.Typer()


@app.command()
def init_index_terms(path: Path):
    with InvertedIndex.load() as inverted_index:
        inverted_index: InvertedIndex
        inverted_index.replace_index_terms(path)


@app.command()
def index_text_corpus(corpus_path: Path = Path("text_corpus")):
    with InvertedIndex.load() as inverted_index:
        inverted_index: InvertedIndex
        inverted_index.index_text_corpus(corpus_path)


@app.command()
def search_boolean(normal_conjunctive: str):
    with InvertedIndex.load() as inverted_index:
        inverted_index: InvertedIndex
        result = inverted_index.search(normal_conjunctive)
        if len(result) == 0:
            print("Documents not found :(")
            return
        print("Found documents:")
        for item in result:
            print(item)

@app.command()
def replace_vector_index_terms(path: Path = "initial_index_terms.json"):
    with VectorIndex.load() as vector_index:
        vector_index: VectorIndex
        vector_index.replace_index_terms(path)

@app.command()
def index_text_corpus_vector(corpus_path: Path = Path("text_corpus")):
    with VectorIndex.load() as vector_index:
        vector_index: VectorIndex
        vector_index.index_text_corpus(corpus_path)

@app.command()
def search_vector(query: str):
    with VectorIndex.load() as vector_index:
        vector_index: VectorIndex
        result = vector_index.search(query)
        print("Found documents:")
        for item, score in result:
            print(f"{item}; Score: {score}")

if __name__ == "__main__":
    app()
