import asyncio
import itertools
from typing import AsyncGenerator, Callable, Iterable, List, Tuple, Type, TypeVar

from reactive.agentools import afinish_non_optional
from reactive.stream import GeneratorFinish, StreamGenerator

T = TypeVar("T")
TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)
TException = TypeVar("TException", bound=BaseException)


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


def catch(
    exc_type: Type[TException], handler: Callable[[TException], Iterable[T]]
) -> StreamGenerator[T, T]:
    """
    Catches any raised exception that is an instance of the given type (or one of its subclasses), then continues processing inputs.
    
    The exception is passed to the given handler, which turns it into a stream of values to be yielded. The stream may yield any number of values.
    """

    assert not issubclass(exc_type, GeneratorExit)

    async def _catch(
        exc_type: Type[TException], handler: Callable[[TException], Iterable[T]]
    ) -> AsyncGenerator[Iterable[T], T]:
        value: Iterable[T] = []

        while True:
            try:
                value = [(yield value)]
            except GeneratorExit:
                break
            except exc_type as err:
                value = handler(err)

    return StreamGenerator(_catch(exc_type, handler))


def do(
    next: Callable[[T], None] = lambda _: None,
    error: Callable[[BaseException], None] = lambda _: None,
    completed: Callable[[], None] = lambda: None,
) -> StreamGenerator[T, T]:
    """
    Injects side effects for different stream events, without modifying the stream itself:

    * `next` is invoked whenever a new input arrives at the stream
    * `error` is invoked whenever an exception is raised in the stream (after which the stream will re-raise it and exit)
    * `completed` is invoked when the stream is shutting down _other than_ from an exception

    The stream passes through its inputs in the same order they were received.
    """

    async def _do(
        next: Callable[[T], None],
        error: Callable[[BaseException], None],
        completed: Callable[[], None],
    ) -> AsyncGenerator[Iterable[T], T]:
        result: Iterable[T] = []

        while True:
            try:
                value = yield result
            except GeneratorExit:
                completed()
                break
            except BaseException as err:
                error(err)
                raise
            else:
                next(value)
                result = [value]

    return StreamGenerator(_do(next, error, completed))


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


def broadcast(*streams: StreamGenerator[TOut, TIn]) -> StreamGenerator[TOut, TIn]:
    """
    Distributes each input value to all of the given streams, to process in parallel, then yields an iterable which will provide all of the output values as they return.

    Within the yielded iterable, output values may arrive in a different order than `streams` is specified, as well as an inconsistent order per input value.

    If an exception is raised in the returned generator, it will be raised in turn in each of the streams. Any outputs from those streams will be yielded, after which broadcast() will re-raise the exception.
    """

    async def _broadcast(
        streams: Tuple[StreamGenerator[TOut, TIn], ...]
    ) -> AsyncGenerator[Iterable[TOut], TIn]:
        result: Iterable[TOut] = []

        while True:
            try:
                value = yield result
                it = asyncio.as_completed((stream.asend(value) for stream in streams))
                result = itertools.chain.from_iterable((f.result() for f in it))
            except GeneratorFinish:
                # TODO: What if a stream wants to yield None here?
                it = asyncio.as_completed(
                    (afinish_non_optional(stream) for stream in streams)
                )
                yield itertools.chain.from_iterable(
                    (f.result() for f in it if f.exception() is None)
                )
                break
            except GeneratorExit:
                await asyncio.gather((stream.aclose() for stream in streams))
            except BaseException as err:
                it = asyncio.as_completed(
                    (
                        stream.athrow(type(err), err, err.__traceback__)
                        for stream in streams
                    )
                )
                yield itertools.chain.from_iterable(
                    (f.result() for f in it if f.exception() is None)
                )
                raise

    return StreamGenerator(_broadcast(streams))
