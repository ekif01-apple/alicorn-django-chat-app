from django.db import transaction
from django.db.models import Count

from .models import Conversation, ConversationMember


@transaction.atomic
def get_or_create_dm(me, other):
    qs = (
        Conversation.objects.filter(conversationmember__user=me)
        .filter(conversationmember__user=other)
        .annotate(member_count=Count("conversationmember"))
        .filter(member_count=2)
        .distinct()
    )
    convo = qs.first()
    if convo:
        return convo, False

    convo = Conversation.objects.create()
    ConversationMember.objects.create(conversation=convo, user=me)
    ConversationMember.objects.create(conversation=convo, user=other)
    return convo, True
