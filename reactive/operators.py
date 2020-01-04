from typing import (
    AsyncGenerator,
    AsyncIterable,
    Callable,
    Generic,
    Optional,
    Type,
    TypeVar,
)
from types import TracebackType
import inspect

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


async def chain(
    gen1: AsyncGenerator[U, T], gen2: AsyncGenerator[V, U]
) -> AsyncGenerator[V, T]:
    await gen1.__anext__()
    try:
        await gen2.__anext__()
        try:
            result: V = None  # type: ignore
            # (yield is funky like that)

            while True:
                t = yield result
                u = await gen1.asend(t)
                v = await gen2.asend(u)
        finally:
            await gen2.aclose()
    finally:
        await gen1.aclose()


class ComposableAsyncGenerator(AsyncGenerator[TOut, TIn], Generic[TOut, TIn]):
    """
    Wraps an AsyncGenerator to add some operator overloads to it.
    """

    def __init__(self, agen: AsyncGenerator[TOut, TIn]):
        self._agen = agen
        super().__init__()

    async def __anext__(self) -> TOut:
        return await self._agen.__anext__()

    async def asend(self, x: TIn) -> TOut:
        return await self._agen.asend(x)

    async def athrow(
        self,
        exc_type: Type[BaseException],
        exc_value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
    ) -> TOut:
        return await self._agen.athrow(exc_type, exc_value, traceback)

    async def aclose(self) -> None:
        await self._agen.aclose()

    TOut2 = TypeVar("TOut2", covariant=True)

    def __or__(self, other: AsyncGenerator[TOut2, TOut]) -> AsyncGenerator[TOut2, TIn]:
        if not inspect.isasyncgen(other):
            return NotImplemented

        return chain(self, other)


async def map(fn: Callable[[TIn], TOut]) -> AsyncGenerator[TOut, TIn]:
    result: TOut = None  # type: ignore
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
    gen: AsyncGenerator[TOut, TIn], upstream: AsyncIterable[TIn]
) -> AsyncIterable[TOut]:
    await gen.__anext__()
    async for t in upstream:
        u = await gen.asend(t)
        yield u

    await gen.aclose()
