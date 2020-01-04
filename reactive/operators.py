from typing import AsyncGenerator, Callable, Iterable, List, TypeVar

from reactive.stream import GeneratorFinish, StreamGenerator

T = TypeVar("T")
TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


def map(fn: Callable[[TIn], TOut]) -> StreamGenerator[TOut, TIn]:
    """
    Creates a stream generator which maps over its inputs using the given function.
    
    Each stream yielded will have exactly one item: the mapped value.
    """

    async def _map(fn: Callable[[TIn], TOut]) -> AsyncGenerator[Iterable[TOut], TIn]:
        out_value: Iterable[TOut] = []

        while True:
            in_value = yield out_value
            out_value = (fn(x) for x in [in_value])

    return StreamGenerator(_map(fn))


def filter(fn: Callable[[T], bool]) -> StreamGenerator[T, T]:
    """
    Creates a stream generator which filters its inputs using the given predicate.

    Only inputs matching the predicate will be included in the output. Each stream yielded may have zero or one value, depending on whether the predicate passed on the input.
    """

    async def _filter(fn: Callable[[T], bool]) -> AsyncGenerator[Iterable[T], T]:
        out_value: Iterable[T] = []

        while True:
            in_value = yield out_value
            out_value = (x for x in [in_value] if fn(x))

    return StreamGenerator(_filter(fn))


def collect() -> StreamGenerator[List[T], T]:
    """
    Creates a stream generator which accumulates all of its inputs into a single list, which is yielded only after the full input is consumed.

    While the input is still being consumed, each stream yielded will have zero values. Once the input is exhausted, one stream will be yielded containing one list of all the input values received.
    """

    async def _collect() -> AsyncGenerator[Iterable[List[T]], T]:
        values: List[T] = []

        try:
            while True:
                x = yield []
                values.append(x)
        except GeneratorFinish:
            yield [values]
            raise

    return StreamGenerator(_collect())
