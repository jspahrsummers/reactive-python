from typing import AsyncIterable, AsyncIterator, Iterable, NoReturn, TypeVar

T = TypeVar("T")


async def from_iterable(it: Iterable[T]) -> AsyncIterable[T]:
    """
    Lifts a synchronous iterable into an asynchronous iterable, without otherwise changing its behavior. This is useful for composing with async-only functionality.
    """

    for x in it:
        yield x


def empty() -> AsyncIterable[None]:
    """
    Returns an asynchronous iterable that yields zero values.
    """

    class Empty(AsyncIterator[None]):
        def __aiter__(self) -> AsyncIterator[None]:
            return self

        async def __anext__(self) -> NoReturn:
            raise StopAsyncIteration

    return Empty()


def just(*args: T) -> AsyncIterable[T]:
    """
    Returns an asynchronous iterable which yields the given values, in order.
    """

    return from_iterable(args)
