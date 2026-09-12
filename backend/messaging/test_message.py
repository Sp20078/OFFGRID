from backend.messaging.message import Message, MessageStatus


def test_message_creation():
    message = Message.create(
        source="A",
        destination="E",
        payload="Emergency at Block B"
    )

    assert message.source == "A"
    assert message.destination == "E"
    assert message.payload == "Emergency at Block B"
    assert message.ttl == 8
    assert message.status == MessageStatus.PENDING


def test_ttl():
    message = Message.create(
        source="A",
        destination="E",
        payload="Test",
        ttl=2
    )

    message.decrement_ttl()
    assert message.ttl == 1
    assert not message.is_expired()

    message.decrement_ttl()
    assert message.ttl == 0
    assert message.is_expired()


def test_serialization():
    message = Message.create(
        source="A",
        destination="E",
        payload="Hello"
    )

    data = message.to_json()
    restored = Message.from_json(data)

    assert restored.message_id == message.message_id
    assert restored.source == message.source
    assert restored.destination == message.destination
    assert restored.payload == message.payload