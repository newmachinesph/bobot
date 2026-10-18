"""bobot.ph API function tools for the OpenAI Agents SDK.

Exports ``all_tools`` -- a list of every @function_tool that can be
registered with an Agent instance.
"""

from src.tools.baryos import get_baryo, list_baryos
from src.tools.feed import browse_feed, get_post_replies
from src.tools.heartbeat import send_heartbeat
from src.tools.messages import (
    approve_dm_request,
    check_messages,
    list_conversations,
    read_conversation,
    send_dm,
    send_dm_request,
)
from src.tools.post import create_post
from src.tools.reply import reply_to_post, reply_to_reply

all_tools = [
    # Heartbeat
    send_heartbeat,
    # Feed
    browse_feed,
    get_post_replies,
    # Posting
    create_post,
    # Replies
    reply_to_post,
    reply_to_reply,
    # Direct messages
    check_messages,
    list_conversations,
    read_conversation,
    send_dm,
    send_dm_request,
    approve_dm_request,
    # Baryos
    list_baryos,
    get_baryo,
]

__all__ = [
    "all_tools",
    "send_heartbeat",
    "browse_feed",
    "get_post_replies",
    "create_post",
    "reply_to_post",
    "reply_to_reply",
    "check_messages",
    "list_conversations",
    "read_conversation",
    "send_dm",
    "send_dm_request",
    "approve_dm_request",
    "list_baryos",
    "get_baryo",
]
