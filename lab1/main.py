import typer
from inverted_index import InvertedIndex
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
def search(normal_conjunctive: str):
    with InvertedIndex.load() as inverted_index:
        inverted_index: InvertedIndex
        result = inverted_index.search(normal_conjunctive)
        if len(result) == 0:
            print("Documents not found :(")
            return
        print("Found documents:")
        for item in result:
            print(item)


if __name__ == "__main__":
    app()