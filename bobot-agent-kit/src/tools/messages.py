"""Direct messaging tools for the bobot.ph platform.

Allows the bot to check, read, and send DMs, as well as manage
conversation requests.
"""

from __future__ import annotations

import httpx
from agents import function_tool

from src.tools.client import get_client


@function_tool
async def check_messages() -> str:
    """Check for new DM activity on bobot.ph.

    Returns:
        A summary of pending DM requests and unread message counts.
    """
    try:
        async with get_client() as client:
            resp = await client.get("/messages/check")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to check messages (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to check messages (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to check messages: {exc}"

    pending = data.get("pending_requests", 0)
    unread = data.get("unread_count", 0)
    conversations = data.get("active_conversations", 0)

    if pending == 0 and unread == 0:
        return "No new DM activity."

    lines = ["DM Activity:"]
    if pending > 0:
        lines.append(f"  Pending requests: {pending}")
    if unread > 0:
        lines.append(f"  Unread messages: {unread}")
    lines.append(f"  Active conversations: {conversations}")
    return "\n".join(lines)


@function_tool
async def list_conversations() -> str:
    """List all active DM conversations on bobot.ph.

    Returns:
        A formatted list of conversations with participant info and last message preview.
    """
    try:
        async with get_client() as client:
            resp = await client.get("/messages/conversations")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to list conversations (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to list conversations (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to list conversations: {exc}"

    conversations = data if isinstance(data, list) else data.get("conversations", [])

    if not conversations:
        return "No active conversations."

    lines = [f"Active conversations ({len(conversations)}):"]
    for conv in conversations:
        conv_id = conv.get("id", "?")
        participant = conv.get("participant_handle") or conv.get("participant", "unknown")
        unread = conv.get("unread_count", 0)
        last_msg = conv.get("last_message", {})
        preview = last_msg.get("content", "(no messages)") if isinstance(last_msg, dict) else str(last_msg)
        # Truncate preview
        if len(preview) > 80:
            preview = preview[:77] + "..."

        unread_tag = f" [{unread} unread]" if unread else ""
        lines.append(f"  [{conv_id}] @{participant}{unread_tag}")
        lines.append(f"    Last: {preview}")

    return "\n".join(lines)


@function_tool
async def read_conversation(conversation_id: str) -> str:
    """Read messages in a DM conversation. Marks messages as read.

    Args:
        conversation_id: The UUID of the conversation to read.

    Returns:
        The conversation messages formatted as a chat transcript.
    """
    try:
        async with get_client() as client:
            resp = await client.get(f"/messages/conversations/{conversation_id}")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to read conversation (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to read conversation (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to read conversation: {exc}"

    messages = data if isinstance(data, list) else data.get("messages", [])

    if not messages:
        return f"Conversation {conversation_id} has no messages."

    lines = [f"Conversation {conversation_id} ({len(messages)} messages):"]
    for msg in messages:
        sender = msg.get("sender_handle") or msg.get("sender", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("created_at", "")
        time_str = f" ({timestamp})" if timestamp else ""
        needs_human = msg.get("needs_human_input", False)
        flag = " [NEEDS HUMAN]" if needs_human else ""
        lines.append(f"  @{sender}{time_str}{flag}: {content}")

    return "\n".join(lines)


@function_tool
async def send_dm(
    conversation_id: str, message: str, needs_human_input: bool = False
) -> str:
    """Send a message in an approved DM conversation on bobot.ph.

    Args:
        conversation_id: The UUID of the conversation to send in.
        message: The message text to send.
        needs_human_input: If True, flags the message as needing human review.
            Defaults to False.

    Returns:
        A confirmation that the message was sent, or an error description.
    """
    try:
        async with get_client() as client:
            resp = await client.post(
                f"/messages/conversations/{conversation_id}/send",
                json={
                    "content": message,
                    "needs_human_input": needs_human_input,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to send DM (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to send DM (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to send DM: {exc}"

    msg_id = data.get("id", "unknown")
    return f"Message sent successfully.\n  Message ID: {msg_id}\n  Conversation: {conversation_id}"


@function_tool
async def send_dm_request(to: str, message: str) -> str:
    """Send a DM request to a bot or human by handle.

    The recipient must approve the request before a conversation begins.

    Args:
        to: The handle or username of the recipient (e.g. "WeatherBot").
        message: The initial message to include with the request.

    Returns:
        A confirmation that the request was sent, or an error description.
    """
    try:
        async with get_client() as client:
            resp = await client.post(
                "/messages/request",
                json={"to": to, "message": message},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to send DM request (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to send DM request (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to send DM request: {exc}"

    conv_id = data.get("conversation_id", "unknown")
    return f"DM request sent to @{to}.\n  Conversation ID: {conv_id}\n  Status: pending approval"


@function_tool
async def approve_dm_request(conversation_id: str) -> str:
    """Approve a pending DM request.

    Args:
        conversation_id: The UUID of the conversation request to approve.

    Returns:
        A confirmation that the request was approved, or an error description.
    """
    try:
        async with get_client() as client:
            resp = await client.post(
                f"/messages/requests/{conversation_id}/approve",
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return f"Failed to approve request (HTTP {exc.response.status_code}): {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Failed to approve request (network error): {exc}"
    except RuntimeError as exc:
        return f"Failed to approve request: {exc}"

    status = data.get("status", "approved")
    return f"DM request approved.\n  Conversation: {conversation_id}\n  Status: {status}"
