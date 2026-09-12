from backend.messaging.delivery import DeliveryManager
from backend.messaging.test_router import MockRouter
from backend.messaging.message import MessageStatus


def test_store_and_forward():
    router = MockRouter()
    manager = DeliveryManager(router)

    router.remove_node("E")

    message = manager.create_message(
        source="A",
        destination="E",
        payload="Emergency evacuation"
    )

    delivered = manager.deliver(message)

    assert delivered is False
    assert manager.queue.size("E") == 1
    assert message.status == MessageStatus.PENDING

    router.add_node("E")

    delivered_messages = manager.retry_pending("E")

    assert message.message_id in delivered_messages
    assert message.status == MessageStatus.FORWARDED
    assert manager.queue.size("E") == 0


def test_expired_message_is_not_forwarded():
    router = MockRouter()
    manager = DeliveryManager(router)

    router.add_node("E")

    message = manager.create_message(
        source="A",
        destination="E",
        payload="Expired message",
        ttl=1
    )

    message.decrement_ttl()

    delivered = manager.deliver(message)

    assert delivered is False
    assert message.status == MessageStatus.EXPIRED