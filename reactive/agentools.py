import asyncio
from datetime import timedelta
from types import TracebackType
from typing import (
    AsyncGenerator,
    AsyncIterable,
    Callable,
    Generic,
    Optional,
    Type,
    TypeVar,
)

TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


class GeneratorFinish(GeneratorExit):
    """
    Raised in asynchronous generators by some library functions, to give them an opportunity to flush final values before exiting (which is not permitted in response to GeneratorExit alone).
    """

    pass


class TimeoutError(Exception):
    pass


class TimeoutGenerator(AsyncGenerator[TOut, TIn], Generic[TOut, TIn]):
    """
    This asynchronous generator wraps another generator to enforce that each successive value is delivered within a specified time window. If the timeout is violated, a reactive.agentools.TimeoutError exception is raised within the inner generator.
    """

    _timer_task: Optional[asyncio.Task[None]] = None

    def __init__(self, agen: AsyncGenerator[TOut, TIn], timeout: timedelta):
        self._agen = agen
        self._timeout = timeout
        super().__init__()

    def __aiter__(self) -> "TimeoutGenerator[TOut, TIn]":
        return self

    async def _start_timer(self) -> None:
        async def _timer() -> None:
            await asyncio.sleep(self._timeout.total_seconds())
            await self.athrow(TimeoutError)

        self._timer_task = asyncio.create_task(_timer())

    async def _cancel_timer(self) -> None:
        task = self._timer_task
        self._timer_task = None

        if task is not None:
            task.cancel()

    async def __anext__(self) -> TOut:
        await self._cancel_timer()

        x = await self._agen.__anext__()
        await self._start_timer()

        return x

    async def asend(self, value: TIn) -> TOut:
        await self._cancel_timer()

        x = await self._agen.asend(value)
        await self._start_timer()

        return x

    async def athrow(
        self,
        exc_type: Type[BaseException],
        exc_value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
    ) -> TOut:
        await self._cancel_timer()

        x = await self._agen.athrow(exc_type, exc_value, traceback)
        await self._start_timer()

        return x

    async def aclose(self) -> None:
        await self._cancel_timer()
        await self._agen.aclose()


async def afinish(
    agen: AsyncGenerator[TOut, TIn], cause: Optional[BaseException] = None
) -> Optional[TOut]:
    """
    Raises GeneratorFinish inside the generator, then returns whatever final value it yields.
    
    If there is no final value, raises GeneratorExit.
    If the generator is already closed, returns None.
    """

    finish = GeneratorFinish()
    finish.__cause__ = cause

    result = await agen.athrow(type(finish), finish)

    # Generator must exit after we raised GeneratorFinish.
    await agen.aclose()

    return result


async def afinish_non_optional(
    agen: AsyncGenerator[TOut, TIn], cause: Optional[BaseException] = None
) -> TOut:
    """
    Raises GeneratorFinish inside the generator, then returns whatever final value it yields.
    
    If there is no final value, the final value is None, or the generator is already closed, raises GeneratorExit.
    """
    result = await afinish(agen, cause)
    if result is None:
        raise GeneratorExit from cause

    return result
