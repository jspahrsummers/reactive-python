import inspect
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Iterable,
    NoReturn,
    TypeVar,
    Union,
    cast,
)

T = TypeVar("T")
U = TypeVar("U")


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


async def first(ait: AsyncIterable[T], *default: U) -> Union[T, U]:
    """
    Returns the first value yielded by the given iterable. If there are no values yielded, returns the default (if given) or throws an exception.
    """
    try:
        async for val in ait:
            return val
        else:
            if len(default):
                return default[0]

            raise RuntimeError(
                f"Async iterable {ait} is empty, cannot await first value"
            )
    finally:
        # HACK! For whatever reason, `async for` doesn't properly clean up if it's terminated early, so we have to close the generator by hand to avoid exception spam.
        if inspect.isasyncgen(ait):
            await cast(AsyncGenerator[T, Any], ait).aclose()


async def last(ait: AsyncIterable[T], *default: U) -> Union[T, U]:
    """
    Returns the last (final) value yielded by the given iterable. If there are no values yielded, returns the default (if given) or throws an exception.
    """
    result: Union[T, U]
    async for val in ait:
        result = val
    else:
        if not len(default):
            raise RuntimeError(
                f"Async iterable {ait} is empty, cannot await last value"
            )

        result = default[0]

    return result
