from typing import AsyncIterable, Callable, TypeVar

T = TypeVar("T")
U = TypeVar("U")


def map(fn: Callable[[T], U]) -> Callable[[AsyncIterable[T]], AsyncIterable[U]]:
    async def _map(it: AsyncIterable[T]) -> AsyncIterable[U]:
        async for x in it:
            yield fn(x)

    return _map


def filter(fn: Callable[[T], bool]) -> Callable[[AsyncIterable[T]], AsyncIterable[T]]:
    async def _filter(it: AsyncIterable[T]) -> AsyncIterable[T]:
        async for x in it:
            if fn(x):
                yield x

    return _filter
