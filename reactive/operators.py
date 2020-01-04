import inspect
import itertools
import sys
from types import TracebackType
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Generator,
    Generic,
    Iterable,
    Iterator,
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
        try:
            await gen1.__anext__()
            await gen2.__anext__()

            result: Iterable[V] = []

            async def _flatmap(u_values: Iterable[U]) -> List[V]:
                v_values = []
                for u in u_values:
                    for v in await gen2.asend(u):
                        v_values.append(v)

                return v_values

            while True:
                try:
                    t = yield result
                except BaseException as err:
                    exc = sys.exc_info()

                    uit = await gen1.athrow(*exc)
                    if uit:
                        yield await _flatmap(uit)

                    vit = await gen2.athrow(*exc)
                    if vit:
                        yield vit

                    raise
                else:
                    result = await _flatmap(await gen1.asend(t))
        finally:
            await gen1.aclose()
            await gen2.aclose()

    return StreamGenerator(_chain(gen1, gen2))


class AwaitableIterable(Awaitable[TOut], AsyncIterable[TOut], Generic[TOut]):
    def __init__(self, it: AsyncIterable[TOut]):
        self._it = it
        super().__init__()

    def __aiter__(self) -> AsyncIterator[TOut]:
        return self._it.__aiter__()

    def __await__(self) -> Generator[Any, None, TOut]:
        return self.__aiter__().__anext__().__await__()


def connect(
    gen: AsyncGenerator[Iterable[TOut], TIn], upstream: AsyncIterable[TIn]
) -> AwaitableIterable[TOut]:
    async def _connect(
        gen: AsyncGenerator[Iterable[TOut], TIn], upstream: AsyncIterable[TIn]
    ) -> AsyncIterable[TOut]:
        await gen.__anext__()

        try:
            async for t in upstream:
                for u in await gen.asend(t):
                    yield u
        except BaseException:
            it = await gen.athrow(*sys.exc_info())
            if it:
                for u in it:
                    yield u

            raise
        else:
            it = await gen.athrow(GeneratorExit)
            if it:
                for u in it:
                    yield u
        finally:
            await gen.aclose()

    return AwaitableIterable(_connect(gen, upstream))


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

    def __le__(self, upstream: AsyncIterable[TIn]) -> AwaitableIterable[TOut]:
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


def collect() -> StreamGenerator[List[T], T]:
    async def _collect() -> AsyncGenerator[Iterable[List[T]], T]:
        values: List[T] = []

        try:
            while True:
                x = yield []
                values.append(x)
        except GeneratorExit:
            yield [values]
            raise

    return StreamGenerator(_collect())
