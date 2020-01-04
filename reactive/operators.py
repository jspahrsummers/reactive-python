import inspect
import itertools
from types import TracebackType
from typing import (
    AsyncGenerator,
    AsyncIterable,
    Callable,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
)

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


def chain(
    gen1: AsyncGenerator[Iterable[U], T], gen2: AsyncGenerator[Iterable[V], U]
) -> "StreamGenerator[V, T]":
    async def _chain(
        gen1: AsyncGenerator[Iterable[U], T], gen2: AsyncGenerator[Iterable[V], U]
    ) -> AsyncGenerator[Iterable[V], T]:
        await gen1.__anext__()
        try:
            await gen2.__anext__()
            try:
                result: Iterable[V] = []

                while True:
                    t = yield result

                    u_values = await gen1.asend(t)
                    v_values: List[V] = []
                    for u in u_values:
                        for v in await gen2.asend(u):
                            v_values.append(v)

                    result = v_values
            finally:
                await gen2.aclose()
        finally:
            await gen1.aclose()

    return StreamGenerator(_chain(gen1, gen2))


async def connect(
    gen: AsyncGenerator[Iterable[TOut], TIn], upstream: AsyncIterable[TIn]
) -> AsyncIterable[TOut]:
    await gen.__anext__()
    async for t in upstream:
        for u in await gen.asend(t):
            yield u

    await gen.aclose()


class StreamGenerator(AsyncGenerator[Iterable[TOut], TIn], Generic[TOut, TIn]):
    """
    An AsyncGenerator which yields an indefinite number of results per each input.
    """

    def __init__(self, agen: AsyncGenerator[Iterable[TOut], TIn]):
        self._agen = agen
        super().__init__()

    def __aiter__(self) -> "StreamGenerator[TOut, TIn]":
        return self

    async def __anext__(self) -> Iterable[TOut]:
        return await self._agen.__anext__()

    async def asend(self, x: TIn) -> Iterable[TOut]:
        return await self._agen.asend(x)

    async def athrow(
        self,
        exc_type: Type[BaseException],
        exc_value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
    ) -> Iterable[TOut]:
        return await self._agen.athrow(exc_type, exc_value, traceback)

    async def aclose(self) -> None:
        await self._agen.aclose()

    TOut2 = TypeVar("TOut2", covariant=True)

    def __or__(
        self, other: "StreamGenerator[TOut2, TOut]"
    ) -> "StreamGenerator[TOut2, TIn]":
        if not isinstance(other, StreamGenerator):
            return NotImplemented

        return chain(self, other)

    def __le__(self, upstream: AsyncIterable[TIn]) -> AsyncIterable[TOut]:
        if not hasattr(upstream, "__aiter__"):
            return NotImplemented

        return connect(self, upstream)


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
