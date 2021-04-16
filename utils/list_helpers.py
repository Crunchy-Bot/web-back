def chunk_n(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def expand_out_of_lists(doc: dict) -> dict:
    return {
        k: v[0] for k, v in doc.items()
    }
