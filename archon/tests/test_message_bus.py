"""Tests for MessageBus: P2P FIFO zero loss, reactive queueing, broadcast, and lifecycle."""
import asyncio
import pytest

from archon.core.bus import MessageBus
from archon.exceptions import InvalidRecipientError, MessageBusClosedError


class TestMessageBusCore:
    """TDD tests for reactive in-memory MessageBus."""

    @pytest.mark.asyncio
    async def test_p2p_send_and_receive_fifo(self):
        bus = MessageBus()
        bus.register_recipient("agent_a")
        bus.register_recipient("agent_b")

        await bus.send_message("agent_a", "agent_b", "msg 1")
        await bus.send_message("agent_a", "agent_b", "msg 2")
        await bus.send_message("agent_a", "agent_b", "msg 3")

        recv1 = await bus.receive_message("agent_b", timeout=1.0)
        recv2 = await bus.receive_message("agent_b", timeout=1.0)
        recv3 = await bus.receive_message("agent_b", timeout=1.0)

        assert recv1["payload"] == "msg 1"
        assert recv2["payload"] == "msg 2"
        assert recv3["payload"] == "msg 3"
        assert recv1["sender_id"] == "agent_a"
        assert recv1["recipient_id"] == "agent_b"

    @pytest.mark.asyncio
    async def test_send_to_unregistered_recipient_raises_invalid_recipient_error(self):
        bus = MessageBus()
        bus.register_recipient("agent_a")

        with pytest.raises(InvalidRecipientError) as exc_info:
            await bus.send_message("agent_a", "non_existent_agent", "hello")
        assert "non_existent_agent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_broadcast_message_delivers_to_all_recipients(self):
        bus = MessageBus()
        bus.register_recipient("worker_1")
        bus.register_recipient("worker_2")
        bus.register_recipient("worker_3")

        await bus.send_message("orchestrator", "*", "global announcement")

        msg1 = await bus.receive_message("worker_1", timeout=1.0)
        msg2 = await bus.receive_message("worker_2", timeout=1.0)
        msg3 = await bus.receive_message("worker_3", timeout=1.0)

        assert msg1["payload"] == "global announcement"
        assert msg2["payload"] == "global announcement"
        assert msg3["payload"] == "global announcement"

    @pytest.mark.asyncio
    async def test_send_to_closed_message_bus_raises_error(self):
        bus = MessageBus()
        bus.register_recipient("agent_a")
        bus.close()

        with pytest.raises(MessageBusClosedError):
            await bus.send_message("agent_a", "agent_a", "message")

        with pytest.raises(MessageBusClosedError):
            await bus.receive_message("agent_a", timeout=0.1)

    @pytest.mark.asyncio
    async def test_high_volume_concurrent_fifo_zero_loss(self):
        """Verify 1,000 concurrent messages delivered without loss with strict FIFO."""
        bus = MessageBus()
        bus.register_recipient("receiver")

        message_count = 1000

        async def producer():
            for i in range(message_count):
                await bus.send_message("producer", "receiver", i)

        async def consumer():
            received = []
            for _ in range(message_count):
                msg = await bus.receive_message("receiver", timeout=5.0)
                received.append(msg["payload"])
            return received

        producer_task = asyncio.create_task(producer())
        consumer_task = asyncio.create_task(consumer())

        await asyncio.gather(producer_task)
        received_items = await consumer_task

        assert len(received_items) == message_count
        assert received_items == list(range(message_count))
