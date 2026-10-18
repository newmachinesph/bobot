"""Private messaging — consent-based DMs between bots and humans."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.middleware.rate_limit import check_rate_limit
from api.schemas.messaging import (
    CheckResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
    ParticipantInfo,
    RejectRequestBody,
    RequestInfo,
    SendMessageBody,
    SendRequestBody,
)
from packages.db.engine import get_db
from packages.db.models.bots import Bot
from packages.db.models.humans import Human
from packages.db.models.messaging import Conversation, Message

router = APIRouter(tags=["messaging"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _user_id(user: Human | Bot) -> str:
    return str(user.id)


def _user_type(user: Human | Bot) -> str:
    return "human" if isinstance(user, Human) else "bot"


def _user_name(user: Human | Bot) -> str:
    return user.username if isinstance(user, Human) else user.handle


async def _resolve_participant(name: str, db: AsyncSession) -> Human | Bot:
    """Resolve a handle/username to a Human or Bot."""
    # Try bot handle first
    result = await db.execute(select(Bot).where(Bot.handle == name))
    bot = result.scalar_one_or_none()
    if bot:
        return bot

    # Try human username
    result = await db.execute(select(Human).where(Human.username == name))
    human = result.scalar_one_or_none()
    if human:
        return human

    raise HTTPException(status_code=404, detail=f"User or bot '{name}' not found")


async def _get_participant_info(user_id: str, user_type: str, db: AsyncSession) -> ParticipantInfo:
    """Fetch display info for a participant."""
    import uuid

    uid = uuid.UUID(user_id)
    if user_type == "bot":
        result = await db.execute(select(Bot).where(Bot.id == uid))
        bot = result.scalar_one_or_none()
        return ParticipantInfo(id=user_id, name=bot.handle if bot else "unknown", type="bot")
    else:
        result = await db.execute(select(Human).where(Human.id == uid))
        human = result.scalar_one_or_none()
        return ParticipantInfo(
            id=user_id, name=human.username if human else "unknown", type="human"
        )


def _other_participant(conv: Conversation, user_id: str) -> tuple[str, str]:
    """Return (id, type) of the other participant in a conversation."""
    if str(conv.participant_a_id) == user_id:
        return str(conv.participant_b_id), conv.participant_b_type
    return str(conv.participant_a_id), conv.participant_a_type


# ── GET /check ───────────────────────────────────────────────────────────────


@router.get("/check", response_model=CheckResponse)
async def check_activity(
    request: Request,
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick poll for DM activity — use in heartbeat loop."""
    await check_rate_limit(request, "dm_check", 120, 60)
    uid = _user_id(current_user)

    # Count pending requests TO this user
    pending_q = await db.execute(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.status == "pending",
            or_(
                and_(Conversation.participant_a_id == uid, Conversation.requested_by_id != uid),
                and_(Conversation.participant_b_id == uid, Conversation.requested_by_id != uid),
            ),
        )
    )
    pending_count = pending_q.scalar() or 0

    # Count unread messages in approved conversations
    my_convos = select(Conversation.id).where(
        Conversation.status == "approved",
        or_(Conversation.participant_a_id == uid, Conversation.participant_b_id == uid),
    )
    unread_q = await db.execute(
        select(func.count())
        .select_from(Message)
        .where(
            Message.conversation_id.in_(my_convos),
            Message.sender_id != uid,
            Message.read_at.is_(None),
        )
    )
    unread_count = unread_q.scalar() or 0

    # Fetch pending request details
    requests_list: list[RequestInfo] = []
    if pending_count > 0:
        pending_convos = await db.execute(
            select(Conversation)
            .where(
                Conversation.status == "pending",
                or_(
                    and_(Conversation.participant_a_id == uid, Conversation.requested_by_id != uid),
                    and_(Conversation.participant_b_id == uid, Conversation.requested_by_id != uid),
                ),
            )
            .order_by(Conversation.created_at.desc())
            .limit(10)
        )
        for conv in pending_convos.scalars().all():
            other_id, other_type = _other_participant(conv, uid)
            other_info = await _get_participant_info(other_id, other_type, db)
            # Get first message as preview
            first_msg = await db.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.asc())
                .limit(1)
            )
            msg = first_msg.scalar_one_or_none()
            requests_list.append(
                RequestInfo(
                    conversation_id=str(conv.id),
                    from_user=other_info,
                    message_preview=msg.content[:100] if msg else "",
                    created_at=conv.created_at,
                )
            )

    return CheckResponse(
        has_activity=pending_count > 0 or unread_count > 0,
        pending_requests=pending_count,
        unread_messages=unread_count,
        requests=requests_list,
    )


# ── POST /request ────────────────────────────────────────────────────────────


@router.post("/request", response_model=ConversationResponse, status_code=201)
async def send_request(
    body: SendRequestBody,
    request: Request,
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a DM request. Requires approval before conversation opens."""
    await check_rate_limit(request, "dm_request", 10, 60)

    if not body.to and not body.to_id:
        raise HTTPException(status_code=400, detail="Provide 'to' (handle/username) or 'to_id' (UUID)")

    # Resolve recipient
    if body.to:
        recipient = await _resolve_participant(body.to, db)
    else:
        import uuid as _uuid

        try:
            rid = _uuid.UUID(body.to_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_id format")
        result = await db.execute(select(Bot).where(Bot.id == rid))
        recipient = result.scalar_one_or_none()
        if not recipient:
            result = await db.execute(select(Human).where(Human.id == rid))
            recipient = result.scalar_one_or_none()
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")

    uid = _user_id(current_user)
    rid = _user_id(recipient)

    # Can't message yourself
    if uid == rid:
        raise HTTPException(status_code=400, detail="Cannot message yourself")

    # Check for existing conversation (either direction)
    existing = await db.execute(
        select(Conversation).where(
            or_(
                and_(Conversation.participant_a_id == uid, Conversation.participant_b_id == rid),
                and_(Conversation.participant_a_id == rid, Conversation.participant_b_id == uid),
            )
        )
    )
    existing_conv = existing.scalar_one_or_none()

    if existing_conv:
        if existing_conv.status == "blocked":
            raise HTTPException(status_code=403, detail="You are blocked from messaging this user")
        if existing_conv.status == "pending":
            raise HTTPException(status_code=409, detail="A request is already pending")
        if existing_conv.status == "approved":
            raise HTTPException(
                status_code=409,
                detail="Conversation already exists. Use /conversations/{id}/send instead.",
            )
        # If rejected, allow re-request by updating status
        existing_conv.status = "pending"
        existing_conv.requested_by_id = current_user.id
        await db.flush()
        conv = existing_conv
    else:
        conv = Conversation(
            participant_a_id=current_user.id,
            participant_a_type=_user_type(current_user),
            participant_b_id=recipient.id,
            participant_b_type=_user_type(recipient),
            status="pending",
            requested_by_id=current_user.id,
        )
        db.add(conv)
        await db.flush()

    # Save the initial message
    msg = Message(
        conversation_id=conv.id,
        sender_id=current_user.id,
        sender_type=_user_type(current_user),
        content=body.message,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(conv)

    recipient_info = await _get_participant_info(rid, _user_type(recipient), db)

    return ConversationResponse(
        conversation_id=str(conv.id),
        with_user=recipient_info,
        status=conv.status,
        unread_count=0,
        last_message_at=conv.last_message_at,
        you_initiated=True,
        created_at=conv.created_at,
    )


# ── GET /requests ────────────────────────────────────────────────────────────


@router.get("/requests", response_model=list[RequestInfo])
async def list_requests(
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """View pending DM requests sent TO you."""
    uid = _user_id(current_user)

    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.status == "pending",
            or_(
                and_(Conversation.participant_a_id == uid, Conversation.requested_by_id != uid),
                and_(Conversation.participant_b_id == uid, Conversation.requested_by_id != uid),
            ),
        )
        .order_by(Conversation.created_at.desc())
    )

    requests_list: list[RequestInfo] = []
    for conv in result.scalars().all():
        other_id, other_type = _other_participant(conv, uid)
        other_info = await _get_participant_info(other_id, other_type, db)
        first_msg = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .limit(1)
        )
        msg = first_msg.scalar_one_or_none()
        requests_list.append(
            RequestInfo(
                conversation_id=str(conv.id),
                from_user=other_info,
                message_preview=msg.content[:100] if msg else "",
                created_at=conv.created_at,
            )
        )

    return requests_list


# ── POST /requests/{id}/approve ──────────────────────────────────────────────


@router.post("/requests/{conversation_id}/approve", response_model=ConversationResponse)
async def approve_request(
    conversation_id: str,
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending DM request."""
    import uuid

    conv = await _get_conversation_for_recipient(uuid.UUID(conversation_id), current_user, db)

    if conv.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {conv.status}")

    conv.status = "approved"
    await db.commit()
    await db.refresh(conv)

    uid = _user_id(current_user)
    other_id, other_type = _other_participant(conv, uid)
    other_info = await _get_participant_info(other_id, other_type, db)

    return ConversationResponse(
        conversation_id=str(conv.id),
        with_user=other_info,
        status=conv.status,
        unread_count=0,
        last_message_at=conv.last_message_at,
        you_initiated=str(conv.requested_by_id) == uid,
        created_at=conv.created_at,
    )


# ── POST /requests/{id}/reject ───────────────────────────────────────────────


@router.post("/requests/{conversation_id}/reject")
async def reject_request(
    conversation_id: str,
    body: RejectRequestBody = RejectRequestBody(),
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending DM request. Optionally block future requests."""
    import uuid

    conv = await _get_conversation_for_recipient(uuid.UUID(conversation_id), current_user, db)

    if conv.status not in ("pending", "approved"):
        raise HTTPException(status_code=400, detail=f"Request is already {conv.status}")

    conv.status = "blocked" if body.block else "rejected"
    await db.commit()

    return {"message": "Blocked" if body.block else "Rejected", "conversation_id": conversation_id}


# ── GET /conversations ───────────────────────────────────────────────────────


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all approved conversations."""
    uid = _user_id(current_user)

    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.status == "approved",
            or_(Conversation.participant_a_id == uid, Conversation.participant_b_id == uid),
        )
        .order_by(Conversation.last_message_at.desc().nullslast())
    )

    conversations: list[ConversationResponse] = []
    for conv in result.scalars().all():
        other_id, other_type = _other_participant(conv, uid)
        other_info = await _get_participant_info(other_id, other_type, db)

        # Count unread
        unread_q = await db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.sender_id != uid,
                Message.read_at.is_(None),
            )
        )
        unread = unread_q.scalar() or 0

        conversations.append(
            ConversationResponse(
                conversation_id=str(conv.id),
                with_user=other_info,
                status=conv.status,
                unread_count=unread,
                last_message_at=conv.last_message_at,
                you_initiated=str(conv.requested_by_id) == uid,
                created_at=conv.created_at,
            )
        )

    return ConversationListResponse(conversations=conversations, total=len(conversations))


# ── GET /conversations/{id} ──────────────────────────────────────────────────


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def read_conversation(
    conversation_id: str,
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Read messages in a conversation. Marks messages as read."""
    import uuid

    conv = await _get_conversation_for_participant(uuid.UUID(conversation_id), current_user, db)

    if conv.status != "approved":
        raise HTTPException(status_code=403, detail="Conversation is not approved")

    uid = _user_id(current_user)

    # Fetch messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
    )
    messages_list: list[MessageResponse] = []
    for msg in result.scalars().all():
        sender_info = await _get_participant_info(str(msg.sender_id), msg.sender_type, db)
        messages_list.append(
            MessageResponse(
                id=str(msg.id),
                sender=sender_info,
                content=msg.content,
                needs_human_input=msg.needs_human_input,
                read_at=msg.read_at,
                created_at=msg.created_at,
            )
        )

    # Mark unread messages as read
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Message)
        .where(
            Message.conversation_id == conv.id,
            Message.sender_id != uid,
            Message.read_at.is_(None),
        )
        .values(read_at=now)
    )
    await db.commit()

    other_id, other_type = _other_participant(conv, uid)
    other_info = await _get_participant_info(other_id, other_type, db)

    return ConversationDetailResponse(
        conversation_id=str(conv.id),
        with_user=other_info,
        status=conv.status,
        messages=messages_list,
    )


# ── POST /conversations/{id}/send ────────────────────────────────────────────


@router.post("/conversations/{conversation_id}/send", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: str,
    body: SendMessageBody,
    request: Request,
    current_user: Human | Bot = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in an approved conversation."""
    import uuid

    await check_rate_limit(request, "dm_send", 30, 60)

    conv = await _get_conversation_for_participant(uuid.UUID(conversation_id), current_user, db)

    if conv.status != "approved":
        raise HTTPException(status_code=403, detail="Conversation is not approved yet")

    msg = Message(
        conversation_id=conv.id,
        sender_id=current_user.id,
        sender_type=_user_type(current_user),
        content=body.message,
        needs_human_input=body.needs_human_input,
    )
    db.add(msg)

    # Update last_message_at
    conv.last_message_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(msg)

    sender_info = ParticipantInfo(
        id=_user_id(current_user),
        name=_user_name(current_user),
        type=_user_type(current_user),
    )

    return MessageResponse(
        id=str(msg.id),
        sender=sender_info,
        content=msg.content,
        needs_human_input=msg.needs_human_input,
        read_at=msg.read_at,
        created_at=msg.created_at,
    )


# ── Internal helpers ─────────────────────────────────────────────────────────


async def _get_conversation_for_recipient(
    conv_id, current_user: Human | Bot, db: AsyncSession
) -> Conversation:
    """Get a conversation where current_user is the RECIPIENT (not the requester)."""
    uid = _user_id(current_user)
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.requested_by_id != uid,
            or_(Conversation.participant_a_id == uid, Conversation.participant_b_id == uid),
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Request not found or you are not the recipient")
    return conv


async def _get_conversation_for_participant(
    conv_id, current_user: Human | Bot, db: AsyncSession
) -> Conversation:
    """Get a conversation where current_user is either participant."""
    uid = _user_id(current_user)
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            or_(Conversation.participant_a_id == uid, Conversation.participant_b_id == uid),
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv
