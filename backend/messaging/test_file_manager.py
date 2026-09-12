from backend.messaging.file_manager import FileTransferManager
from backend.messaging.delivery import DeliveryManager
from backend.messaging.test_router import MockRouter


def test_file_transfer_creates_messages():
    router = MockRouter()
    delivery = DeliveryManager(router)
    transfer = FileTransferManager(delivery, chunk_size=5)

    data = b"OFFGRID EMERGENCY FILE"

    messages = transfer.create_transfer(
        source="A",
        destination="E",
        data=data
    )

    assert len(messages) == 5

    for message in messages:
        assert message.source == "A"
        assert message.destination == "E"
        assert message.sequence >= 0


def test_file_chunks_can_be_received_and_assembled():
    router = MockRouter()
    delivery = DeliveryManager(router)
    transfer = FileTransferManager(delivery, chunk_size=5)

    data = b"OFFGRID EMERGENCY FILE"

    messages = transfer.create_transfer(
        source="A",
        destination="E",
        data=data
    )

    file_id = transfer._decode_chunk(
        messages[0].payload
    ).file_id

    for message in messages:
        result = transfer.receive_chunk(message)
        assert result == "ACCEPTED"

    assert transfer.is_complete(file_id) is True
    assert transfer.assemble_file(file_id) == data


def test_file_chunks_can_arrive_out_of_order():
    router = MockRouter()
    delivery = DeliveryManager(router)
    transfer = FileTransferManager(delivery, chunk_size=4)

    data = b"OFFGRID FILE TRANSFER"

    messages = transfer.create_transfer(
        source="A",
        destination="E",
        data=data
    )

    file_id = transfer._decode_chunk(
        messages[0].payload
    ).file_id

    for message in reversed(messages):
        transfer.receive_chunk(message)

    assert transfer.is_complete(file_id) is True
    assert transfer.assemble_file(file_id) == data


def test_duplicate_file_chunk_is_ignored():
    router = MockRouter()
    delivery = DeliveryManager(router)
    transfer = FileTransferManager(delivery, chunk_size=5)

    data = b"OFFGRID"

    messages = transfer.create_transfer(
        source="A",
        destination="E",
        data=data
    )

    first = messages[0]

    assert transfer.receive_chunk(first) == "ACCEPTED"
    assert transfer.receive_chunk(first) == "DUPLICATE"


def test_invalid_chunk_is_rejected():
    router = MockRouter()
    delivery = DeliveryManager(router)
    transfer = FileTransferManager(delivery)

    message = delivery.create_message(
        source="A",
        destination="E",
        payload="INVALID"
    )

    assert transfer.receive_chunk(message) == "INVALID_CHUNK"
