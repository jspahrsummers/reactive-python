import unittest
from typing import Callable, List

from hypothesis import given
from hypothesis.strategies import integers, lists

import reactive
import tests.helpers
from reactive import op


class TestOperators(tests.helpers.AsyncTestCase):
    @given(lists(integers()))  # type: ignore
    async def test_map(self, items: List[int]) -> None:
        # mypy needs help to infer map() here :(
        fn: Callable[[int], int] = lambda x: x * 2
        ait = op.map(fn)(reactive.from_iterable(items))

        i = 0
        async for x in ait:
            self.assertEqual(x, items[i] * 2)
            i += 1


if __name__ == "__main__":
    unittest.main()
