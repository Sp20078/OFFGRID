import asyncio

import pytest

from backend.network.udp_transport import UDPTransport


@pytest.mark.asyncio
async def test_udp_send_and_receive():
    received = asyncio.Future()

    async def on_message(message, addr):
        if not received.done():
            received.set_result((message, addr))

    receiver = UDPTransport(
        host="127.0.0.1",
        port=0,
        on_message=on_message,
    )

    await receiver.start()

    receiver_port = receiver.transport.get_extra_info("sockname")[1]

    sender = UDPTransport(
        host="127.0.0.1",
        port=0,
    )

    await sender.start()

    sender.send(
        {
            "type": "TEST",
            "payload": "hello",
        },
        "127.0.0.1",
        receiver_port,
    )

    message, address = await asyncio.wait_for(
        received,
        timeout=2,
    )

    assert message["type"] == "TEST"
    assert message["payload"] == "hello"
    assert address[0] == "127.0.0.1"

    await sender.stop()
    await receiver.stop()


@pytest.mark.asyncio
async def test_invalid_udp_payload_is_ignored():
    received = []

    def on_message(message, addr):
        received.append(message)

    receiver = UDPTransport(
        host="127.0.0.1",
        port=0,
        on_message=on_message,
    )

    await receiver.start()

    receiver_port = receiver.transport.get_extra_info("sockname")[1]

    loop = asyncio.get_running_loop()

    raw_transport, _ = await loop.create_datagram_endpoint(
        asyncio.DatagramProtocol,
        remote_addr=("127.0.0.1", receiver_port),
    )

    raw_transport.sendto(
        b"THIS IS NOT JSON",
    )

    await asyncio.sleep(0.1)

    assert received == []

    raw_transport.close()
    await receiver.stop()