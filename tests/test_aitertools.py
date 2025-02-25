import unittest
from typing import Any, Iterable, List

from hypothesis import given
from hypothesis.strategies import from_type, iterables, lists

import tests.helpers
from reactive import aitertools


class TestAItertools(tests.helpers.AsyncTestCase):
    async def test_empty(self) -> None:
        empty = aitertools.empty()

        values: List[None] = []
        async for x in empty:
            values.append(x)

        self.assertEqual(values, [])

    async def test_empty_manual_iteration(self) -> None:
        empty = aitertools.empty()

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

        ait = aitertools.from_iterable((_save(x) for x in it))
        async for x in ait:
            self.assertEqual(x, values.pop(0))

    @given(lists(from_type(type)))  # type: ignore
    async def test_just(self, values: List[Any]) -> None:
        ait = aitertools.just(*values)
        async for x in ait:
            self.assertEqual(x, values.pop(0))


if __name__ == "__main__":
    unittest.main()
