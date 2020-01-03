from typing import AsyncIterable, AsyncIterator, Iterable, NoReturn, TypeVar

T = TypeVar("T")


async def from_iterable(it: Iterable[T]) -> AsyncIterable[T]:
    for x in it:
        yield x


def empty() -> AsyncIterable[None]:
    class Empty(AsyncIterator[None]):
        def __aiter__(self) -> AsyncIterator[None]:
            return self

        async def __anext__(self) -> NoReturn:
            raise StopAsyncIteration

    return Empty()


def just(*args: T) -> AsyncIterable[T]:
    return from_iterable(args)
