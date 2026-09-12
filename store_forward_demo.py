from backend.messaging.delivery import DeliveryManager
from backend.messaging.test_router import MockRouter


router = MockRouter()
manager = DeliveryManager(router)

print("=== OFFGRID STORE-AND-FORWARD DEMO ===")

print("\n[1] Destination E is OFFLINE")
router.remove_node("E")

message = manager.create_message(
    source="A",
    destination="E",
    payload="Emergency evacuation at Block B"
)

print("Message:", message.message_id)
print("Status:", message.status.value)

print("\n[2] Attempting delivery...")
result = manager.deliver(message)

print("Delivered:", result)
print("Queued messages:", manager.queue.size("E"))

print("\n[3] Destination E comes ONLINE")
router.add_node("E")

print("\n[4] Retrying queued messages...")
delivered = manager.retry_pending("E")

print("Delivered messages:", delivered)
print("Final status:", message.status.value)
print("Queued messages:", manager.queue.size("E"))
