import asyncio


batches = {}


def create_batch(batch_id: str, total: int):
    batches[batch_id] = {
        "total": total,
        "completed": 0,
        "results": [],
        "event": asyncio.Event(),
    }


def add_result(batch_id: str, result: dict):

    batch = batches[batch_id]

    batch["results"].append(result)
    batch["completed"] += 1

    if batch["completed"] >= batch["total"]:
        batch["event"].set()


async def wait_for_batch(batch_id: str):

    batch = batches[batch_id]

    await batch["event"].wait()

    return batch["results"]

async def collect_batch_result(batch_id: str):

    results = await wait_for_batch(batch_id)

    print("\n")
    print("=" * 50)
    print(f"BATCH {batch_id} COMPLETED")
    print("=" * 50)

    for result in results:
        print(result)

    print("=" * 50)