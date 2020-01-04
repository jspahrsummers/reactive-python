import unittest
from typing import Callable, Iterable, List

from hypothesis import given
from hypothesis.strategies import integers, iterables, lists

import reactive
import tests.helpers
from reactive import op


class TestOperators(tests.helpers.AsyncTestCase):
    @given(lists(integers()))  # type: ignore
    async def test_map(self, items: List[int]) -> None:
        # mypy needs help to infer map() here :(
        fn: Callable[[int], int] = lambda x: x * 2
        ait = reactive.from_iterable(items) >= op.map(fn)

        i = 0
        async for x in ait:
            self.assertEqual(x, items[i] * 2)
            i += 1

    @given(iterables(integers()))  # type: ignore
    async def test_filter(self, items: Iterable[int]) -> None:
        # mypy needs help to infer filter() here :(
        fn: Callable[[int], bool] = lambda x: x < 0
        ait = op.filter(fn) <= reactive.from_iterable(items)

        async for x in ait:
            self.assertLess(x, 0)


if __name__ == "__main__":
    unittest.main()
