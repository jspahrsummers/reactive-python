import asyncio
import unittest

import aiounittest

import reactive
from typing import List


class TestConstructors(aiounittest.AsyncTestCase):
    async def test_empty(self) -> None:
        empty = reactive.empty()

        values: List[None] = []
        async for x in empty:
            values.append(x)

        self.assertEqual(values, [])

    async def test_empty_manual_iteration(self) -> None:
        empty = reactive.empty()

        it = empty.__aiter__()
        with self.assertRaises(StopAsyncIteration):
            await it.__anext__()


if __name__ == "__main__":
    unittest.main()
