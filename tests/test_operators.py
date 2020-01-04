import unittest
from typing import Callable, Iterable, List

from hypothesis import given
from hypothesis.strategies import integers, iterables, lists

import reactive
import reactive.operators as op
import tests.helpers
from reactive.aitertools import first, from_iterable


class TestOperators(tests.helpers.AsyncTestCase):
    @given(lists(integers()))  # type: ignore
    async def test_map(self, items: List[int]) -> None:
        # mypy needs help to infer map() here :(
        fn: Callable[[int], int] = lambda x: x * 2
        ait = from_iterable(items) >= op.map(fn)

        i = 0
        async for x in ait:
            self.assertEqual(x, items[i] * 2)
            i += 1

    @given(iterables(integers()))  # type: ignore
    async def test_filter(self, items: Iterable[int]) -> None:
        # mypy needs help to infer filter() here :(
        fn: Callable[[int], bool] = lambda x: x < 0
        ait = op.filter(fn) <= from_iterable(items)

        async for x in ait:
            self.assertLess(x, 0)

    @given(iterables(integers()))  # type: ignore
    async def test_filter_map(self, items: Iterable[int]) -> None:
        def is_negative(x: int) -> bool:
            return x < 0

        ait = from_iterable(items) >= op.filter(is_negative) | op.map(str)

        async for x in ait:
            self.assertIsInstance(x, str)
            self.assertLess(int(x), 0)

    @given(iterables(integers()))  # type: ignore
    async def test_collect(self, items: Iterable[int]) -> None:
        def is_negative(x: int) -> bool:
            return x < 0

        filtered = await first(
            from_iterable(items) >= op.filter(is_negative) | op.collect()
        )

        for x in filtered:
            self.assertLess(x, 0)


if __name__ == "__main__":
    unittest.main()
