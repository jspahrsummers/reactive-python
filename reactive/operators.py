import asyncio
import functools
import itertools
from datetime import timedelta
from typing import (
    AsyncGenerator,
    AsyncIterable,
    Callable,
    Iterable,
    List,
    Tuple,
    Type,
    TypeVar,
)

from reactive import aitertools
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
    return lift(functools.partial(aitertools.map, fn))


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


def delay(td: timedelta) -> StreamGenerator[T, T]:
    """
    Delays the delivery of each input value by at least `td`. Does not modify the inputs otherwise.
    """

    async def _delay(td: timedelta) -> AsyncGenerator[Iterable[T], T]:
        result: Iterable[T] = []
        while True:
            result = [(yield result)]
            await asyncio.sleep(td.total_seconds())

    return StreamGenerator(_delay(td))


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


def lift(
    fn: Callable[[AsyncIterable[TIn]], AsyncIterable[TOut]]
) -> StreamGenerator[TOut, TIn]:
    """
    Lifts a transformation over asynchronous iterables into a stream generator. The stream's input values will be transformed like the asynchronous iterable's would be, then yielded--possibly spread across several iterables in the output.
    """

    async def _lift(
        fn: Callable[[AsyncIterable[TIn]], AsyncIterable[TOut]]
    ) -> AsyncGenerator[Iterable[TOut], TIn]:
        in_queue: asyncio.Queue[TIn] = asyncio.Queue(maxsize=1)
        out_queue: asyncio.Queue[TOut] = asyncio.Queue()
        cancelled = asyncio.Event()

        wait_cancelled = asyncio.create_task(cancelled.wait())

        async def _in_iter() -> AsyncIterable[TIn]:
            while not cancelled.is_set():
                try:
                    value = in_queue.get_nowait()
                except asyncio.QueueEmpty:
                    get_task = asyncio.create_task(in_queue.get())

                    done, pending = asyncio.wait(
                        (wait_cancelled, get_task), return_when=asyncio.FIRST_COMPLETED
                    )
                    if cancelled.is_set():
                        return

                    assert get_task in done
                    value = get_task.result()

                yield value
                in_queue.task_done()

        async def _out_loop() -> None:
            async for out in fn(_in_iter()):
                await out_queue.put(out)

        loop_task = asyncio.create_task(_out_loop())

        try:
            outputs: List[TOut] = []

            while True:
                input_value = yield outputs
                for _ in outputs:
                    out_queue.task_done()

                if loop_task.done():
                    # The output iterable finished, so exit gracefully.
                    break

                try:
                    in_queue.put_nowait(input_value)
                except asyncio.QueueFull:
                    put_task = asyncio.create_task(in_queue.put(input_value))
                    asyncio.wait(
                        (loop_task, put_task), return_when=asyncio.FIRST_COMPLETED
                    )

                # This _does not_ guarantee that out_queue has all of the values that may come from the iterable, but it should at least ensure that any synchronous transformations have completed.
                # TODO: Test this
                await in_queue.join()

                outputs = []
                while not out_queue.empty():
                    outputs.append(await out_queue.get())
        except GeneratorFinish:
            await in_queue.join()
            cancelled.set()

            loop_task.cancel()
            await asyncio.wait_for(loop_task, timeout=None)

            yield (out_queue.get_nowait() for _ in range(out_queue.qsize()))
        finally:
            cancelled.set()
            loop_task.cancel()

    return StreamGenerator(_lift(fn))
