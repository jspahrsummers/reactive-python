from typing import AsyncIterable, Iterable, TypeVar

T = TypeVar("T")


async def from_iterable(it: Iterable[T]) -> AsyncIterable[T]:
    for x in it:
        yield x

async def empty() -> AsyncIterable[None]:
    yield

def just(*args: T) -> AsyncIterable[T]:
    return from_iterable(args)
