import aiounittest
import asyncio
from typing import Any, Callable


class AsyncTestCase(aiounittest.AsyncTestCase):
    # Hypothesis hook to run async tests
    def execute_example(self, fn: Callable[[], Any]) -> Any:
        result = fn()

        if asyncio.iscoroutine(result):
            result = asyncio.run(result)

        return result
