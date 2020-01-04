from typing import AsyncGenerator, Callable, Iterable, List, TypeVar

from reactive.stream import StreamGenerator

T = TypeVar("T")
TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


def map(fn: Callable[[TIn], TOut]) -> StreamGenerator[TOut, TIn]:
    async def _map(fn: Callable[[TIn], TOut]) -> AsyncGenerator[Iterable[TOut], TIn]:
        out_value: Iterable[TOut] = []

        while True:
            in_value = yield out_value
            out_value = (fn(x) for x in [in_value])

    return StreamGenerator(_map(fn))


def filter(fn: Callable[[T], bool]) -> StreamGenerator[T, T]:
    async def _filter(fn: Callable[[T], bool]) -> AsyncGenerator[Iterable[T], T]:
        out_value: Iterable[T] = []

        while True:
            in_value = yield out_value
            out_value = (x for x in [in_value] if fn(x))

    return StreamGenerator(_filter(fn))


def collect() -> StreamGenerator[List[T], T]:
    async def _collect() -> AsyncGenerator[Iterable[List[T]], T]:
        values: List[T] = []

        try:
            while True:
                x = yield []
                values.append(x)
        # TODO: Use a custom exception type? Yielding values after GeneratorExit is disallowed according to the docs
        except GeneratorExit:
            yield [values]
            raise

    return StreamGenerator(_collect())
