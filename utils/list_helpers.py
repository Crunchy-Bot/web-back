def chunk_n(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]
