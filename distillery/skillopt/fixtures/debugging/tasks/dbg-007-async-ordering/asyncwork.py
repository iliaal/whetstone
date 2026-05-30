import asyncio


async def _double(x):
    await asyncio.sleep(0)
    return x * 2


async def double_all(values):
    """Return [v*2 for v in values], computed concurrently."""
    results = []
    for v in values:
        task = asyncio.create_task(_double(v))
        results.append(task)
    return results
