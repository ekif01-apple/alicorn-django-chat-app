from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Conversation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # 대화방 변경 시각(자동)
    last_message_at = models.DateTimeField(null=True, blank=True)  # 마지막 메시지 시각

    participants = models.ManyToManyField(
        User,
        through="ConversationMember",
        related_name="conversations",
    )

    def other_user(self, me):
        return self.participants.exclude(id=me.id).first()

    def __str__(self) -> str:
        return f"Conversation({self.id})"


class ConversationMember(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("conversation", "user")]

    def __str__(self) -> str:
        return f"ConversationMember(convo={self.conversation_id}, user={self.user_id})"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["conversation", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Message({self.id}, convo={self.conversation_id})"
