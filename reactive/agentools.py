import asyncio
from typing import AsyncGenerator, AsyncIterable, Callable, Optional, TypeVar

TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


class GeneratorFinish(GeneratorExit):
    """
    Raised in asynchronous generators by some library functions, to give them an opportunity to flush final values before exiting (which is not permitted in response to GeneratorExit alone).
    """

    pass


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


async def lift(
    fn: Callable[[AsyncIterable[TIn]], AsyncIterable[TOut]]
) -> AsyncGenerator[TOut, TIn]:
    """
    Lifts a transformation over asynchronous iterables into a generator. The generator's input values will be transformed like the asynchronous iterable's would be, then yielded.
    """

    in_queue: asyncio.Queue[TIn] = asyncio.Queue(maxsize=1)

    async def in_iter() -> AsyncIterable[TIn]:
        while True:
            yield await in_queue.get()

    out_iter = fn(in_iter())
    out_gen = out_iter.__aiter__()

    x: TOut = None  # type: ignore
    while True:
        await in_queue.put((yield x))
        x = await out_gen.__anext__()
