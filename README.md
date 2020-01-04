# reactive-python

This **proof-of-concept** library builds on top of Python's standard asynchronous iterables, asynchronous generators, and `asyncio` coroutines to offer [reactive programming](https://en.wikipedia.org/wiki/Reactive_programming) abstractions.

The intention is to offer a level of abstraction and compositional power similar to [ReactiveX](http://reactivex.io/), while being directly compatible and composable with the Python standard library.

## Examples

_This library is not production-ready, so the examples will necessarily be toys for now._

Filtering and mapping:

```py
import asyncio
import math
from reactive import aitertools
import reactive.operators as op

async def demo():
    floats = [1.2, float('nan'), 5.4, 6.3, float('inf')]
    strings = aitertools.from_iterable(floats) >= op.filter(math.isfinite) | op.map(str)
    async for s in strings:
        print(s)

asyncio.run(demo())

# Prints:
# 1.2
# 5.4
# 6.3
```

More example usage can be seen in the library's [unit tests](tests/).

## Key concepts

It's a design goal of this library to stay as close to standard Python concepts as possible, while achieving the desired expressivity. Most of the "key concepts" are therefore pre-existing parts of the language or standard library.

### Asynchronous iterables

An [asynchronous iterable][] (represented as `typing.AsyncIterable`) can be looped over with `async for`:

```py
async for s in strings:
    print(s)
```

This is analogous to normal iterables (`typing.Iterable`) and `for ... in ...` loops.

In the context of the `reactive` library, asynchronous iterables are a useful abstraction to represent _a stream of values that may arrive at an indefinite point in time_. Between each iteration of the `async for` loop, execution of the containing [coroutine][] is paused. When the next value is ready, possibly far in the future, the loop resumes.

### Asynchronous generators

An [asynchronous generator][] (represented as `typing.AsyncGenerator`) is like an [asynchronous iterable](#asynchronous-iterables) that can also be [written to](https://docs.python.org/3/reference/expressions.html?highlight=asend#asynchronous-generator-iterator-methods) (just like a normal `typing.Generator`).

In the `reactive` library, _operators_ are implemented as asynchronous generators, so that they can be used to build reactive pipelines. When data is written to an operator, like `map`, it is able to perform any number of transformations or side effects, then output some result.

[Asynchronous generators can be tricky to wrap one's head around](https://docs.python.org/3/reference/expressions.html?highlight=asend#asynchronous-generator-iterator-methods), but luckily they're mostly only important if you want to implement your own operators. Consuming a stream of data, or using the library's provided operators, shouldn't require intimate knowledge of how generators work.

### Stream generators

A stream generator (represented as `reactive.StreamGenerator`) is like a specialized [asynchronous generator](#asynchronous-generators) for use in the `reactive` library.

It's specialized in two ways:

1. **Stream generators always yield `Iterable`s of values**; `StreamGenerator[OutputType, InputType]` is always a subtype of `AsyncGenerator[Iterable[OutputType], InputType]`. This ensures that operators like `reactive.operators.filter` can output a different number of values than they receive as input.
1. **The `StreamGenerator` class comes with a couple of overridden binary operators, `|` and `>=`**, that make building pipelines easier. These are just syntactic sugar, so not strictly necessary to use, but they assist readability.

See the [examples](#examples) above for how this comes together.

## Similar efforts

* **[RxPY](https://github.com/ReactiveX/RxPY)**, the canonical ReactiveX implementation for Python, and much more complete than this project. The tradeoff is that the RxPY [domain-specific language](https://en.wikipedia.org/wiki/Domain-specific_language) is completely orthogonal to existing streaming and concurrency abstractions in Python.
* **[aioreactive](https://github.com/dbrattli/aioreactive)** appears to be an effort by one of the RxPY maintainers to migrate it onto `asyncio` and "[integrate] more naturally with the Python language." Unfortunately, it seems to be abandoned.
* **[aiostream](https://github.com/vxgmichel/aiostream)** sounded appealing to me, but is licensed under the GPLv3. (Consequently, I haven't looked at the code at all and can't vouch for it one way or the other.)

[asynchronous iterable]: https://docs.python.org/3/glossary.html#term-asynchronous-iterable
[asynchronous generator]: https://docs.python.org/3/glossary.html#term-asynchronous-generator
[awaitable]: https://docs.python.org/3/library/asyncio-task.html#awaitables
[coroutine]: https://docs.python.org/3/library/asyncio-task.html#coroutines