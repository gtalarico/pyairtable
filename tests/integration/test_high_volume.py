from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

pytestmark = [pytest.mark.integration]


@pytest.fixture
def table_name():
    return "EVERYTHING"


@pytest.mark.parametrize(
    "thread_count,records_per_thread",
    [
        # (1, 500),
        # (5, 100),
        (25, 20),
    ],
)
def test_high_volume_operations(table, thread_count, records_per_thread):
    """
    Test that we can perform hundreds of batch operations and our
    default retry strategy will catch any 429s (rate limiting).

    If retry_strategy=None, this test will fail.
    """

    def bulk_create(thread_number, record_count):
        created = table.batch_create(
            [
                {"Name": f"thread={thread_number} record={n}"}
                for n in range(record_count)
            ]
        )
        table.batch_delete([record["id"] for record in created])

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [
            executor.submit(bulk_create, thread_number, records_per_thread)
            for thread_number in range(thread_count)
        ]
        all(future.result() for future in as_completed(futures))
