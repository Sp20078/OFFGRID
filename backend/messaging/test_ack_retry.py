from backend.messaging.delivery import DeliveryManager
from backend.messaging.test_router import MockRouter
from backend.messaging.message import MessageStatus


def test_acknowledgement_marks_message_delivered():
    router = MockRouter()
    manager = DeliveryManager(router)

    router.add_node("E")

    message = manager.create_message(
        source="A",
        destination="E",
        payload="Emergency alert"
    )

    assert manager.deliver(message) is True
    assert message.status == MessageStatus.FORWARDED

    result = manager.acknowledge(message.message_id)

    assert result is True
    assert message.status == MessageStatus.DELIVERED


def test_acknowledgement_unknown_message():
    router = MockRouter()
    manager = DeliveryManager(router)

    result = manager.acknowledge("unknown-id")

    assert result is False


def test_retry_count():
    router = MockRouter()
    manager = DeliveryManager(router, max_retries=3)

    message = manager.create_message(
        source="A",
        destination="E",
        payload="Retry test"
    )

    assert manager.get_retry_count(message.message_id) == 0

    router.remove_node("E")

    manager.deliver(message)

    router.add_node("E")

    manager.retry_pending("E")

    assert manager.get_retry_count(message.message_id) == 1


def test_ttl_expiration():
    router = MockRouter()
    manager = DeliveryManager(router)

    message = manager.create_message(
        source="A",
        destination="E",
        payload="TTL test",
        ttl=2
    )

    assert message.ttl == 2

    assert manager.decrement_ttl(message.message_id) is True
    assert message.ttl == 1

    assert manager.decrement_ttl(message.message_id) is False
    assert message.ttl == 0
    assert message.status == MessageStatus.EXPIRED


def test_expired_message_cannot_be_acknowledged():
    router = MockRouter()
    manager = DeliveryManager(router)

    message = manager.create_message(
        source="A",
        destination="E",
        payload="Expired",
        ttl=1
    )

    manager.decrement_ttl(message.message_id)

    result = manager.acknowledge(message.message_id)

    assert result is False
