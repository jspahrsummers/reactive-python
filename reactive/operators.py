from typing import AsyncGenerator, Callable, Iterable, List, TypeVar

from reactive.stream import GeneratorFinish, StreamGenerator

T = TypeVar("T")
TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


def map(fn: Callable[[TIn], TOut]) -> StreamGenerator[TOut, TIn]:
    """
    Maps each input to a new value, using the given function.
    
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
    Passes through only those inputs that satisfy the given predicate.

    Each stream yielded may have zero or one value, depending on whether the predicate passed on the input.
    """

    async def _filter(fn: Callable[[T], bool]) -> AsyncGenerator[Iterable[T], T]:
        out_value: Iterable[T] = []

        while True:
            in_value = yield out_value
            out_value = (x for x in [in_value] if fn(x))

    return StreamGenerator(_filter(fn))


def take(count: int) -> StreamGenerator[T, T]:
    """
    Passes through the first `count` inputs, then exits.
    """

    async def _take(count: int) -> AsyncGenerator[Iterable[T], T]:
        value = yield []
        for i in range(count):
            value = yield [value]

    return StreamGenerator(_take(count))


def drop(count: int) -> StreamGenerator[T, T]:
    """
    Skips the first `count` inputs, then passes through the rest.
    """

    async def _drop(count: int) -> AsyncGenerator[Iterable[T], T]:
        for i in range(count):
            _ = yield []

        result: Iterable[T] = []
        while True:
            result = [(yield result)]

    return StreamGenerator(_drop(count))


def collect() -> StreamGenerator[List[T], T]:
    """
    Accumulates all inputs into a single list, which is yielded only after the full input is consumed.

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
