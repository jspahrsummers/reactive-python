from typing import AsyncGenerator, Optional, TypeVar

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
