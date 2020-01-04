from typing import AsyncGenerator, AsyncIterable, Callable, TypeVar

T = TypeVar("T")
U = TypeVar("U")


async def map(fn: Callable[[T], U]) -> AsyncGenerator[U, T]:
    result: U = None  # type: ignore
    # (yield is funky like that)

    while True:
        x = yield result
        result = fn(x)


def filter(fn: Callable[[T], bool]) -> Callable[[AsyncIterable[T]], AsyncIterable[T]]:
    async def _filter(it: AsyncIterable[T]) -> AsyncIterable[T]:
        async for x in it:
            if fn(x):
                yield x

    return _filter


async def connect(
    gen: AsyncGenerator[U, T], upstream: AsyncIterable[T]
) -> AsyncIterable[U]:
    await gen.__anext__()
    async for t in upstream:
        u = await gen.asend(t)
        yield u

    await gen.aclose()
