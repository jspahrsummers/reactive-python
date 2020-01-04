import asyncio
import unittest
from typing import Any, Callable, Iterable, List, no_type_check_decorator

import aiounittest
from hypothesis import given
from hypothesis.strategies import from_type, iterables, lists

import reactive


class TestConstructors(aiounittest.AsyncTestCase):
    async def test_empty(self) -> None:
        empty = reactive.empty()

        values: List[None] = []
        async for x in empty:
            values.append(x)

        self.assertEqual(values, [])

    async def test_empty_manual_iteration(self) -> None:
        empty = reactive.empty()

        ait = empty.__aiter__()
        with self.assertRaises(StopAsyncIteration):
            await ait.__anext__()

    @given(iterables(from_type(type)))  # type: ignore
    async def test_from_iterable(self, it: Iterable[Any]) -> None:
        # Save aside values as we iterate, so we can test that from_iterable() works with any type of iterable while also validating the output.
        values: List[Any] = []

        def _save(x: Any) -> Any:
            nonlocal values
            values.append(x)
            return x

        ait = reactive.from_iterable((_save(x) for x in it))
        async for x in ait:
            self.assertEqual(x, values.pop(0))

    @given(lists(from_type(type)))  # type: ignore
    async def test_just(self, values: List[Any]) -> None:
        ait = reactive.just(*values)
        async for x in ait:
            self.assertEqual(x, values.pop(0))

    # Hypothesis hook
    def execute_example(self, fn: Callable[[], Any]) -> Any:
        result = fn()

        if asyncio.iscoroutine(result):
            result = asyncio.run(result)

        return result


if __name__ == "__main__":
    unittest.main()
