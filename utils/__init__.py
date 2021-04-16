from .list_helpers import chunk_n


def read_md(file: str):
    with open(file, encoding="UTF-8") as file:
        return file.read()