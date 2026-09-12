from backend.messaging.message import Message, MessageStatus
from backend.messaging.store import MessageStore


def test_message_store():
    store = MessageStore()

    message = Message.create(
        source="A",
        destination="E",
        payload="Emergency"
    )

    store.add(message)

    assert store.get(message.message_id) == message
    assert store.count() == 1


def test_pending_messages():
    store = MessageStore()

    message = Message.create(
        source="A",
        destination="E",
        payload="Emergency"
    )

    store.add(message)

    pending = store.for_destination("E")

    assert len(pending) == 1
    assert pending[0].message_id == message.message_id


def test_mark_delivered():
    store = MessageStore()

    message = Message.create(
        source="A",
        destination="E",
        payload="Emergency"
    )

    store.add(message)
    store.mark_delivered(message.message_id)

    assert message.status == MessageStatus.DELIVERED