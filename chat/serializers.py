from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import Conversation, ConversationMember, Message
from .services import get_or_create_dm

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class MessageSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "body", "created_at"]
        read_only_fields = ["id", "conversation", "sender", "created_at"]


class ConversationListSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "other_user",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
            "last_message_at",
        ]

    def get_other_user(self, obj):
        me = self.context["request"].user
        other = obj.other_user(me)
        return UserPublicSerializer(other).data if other else None

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        return (
            {"id": msg.id, "body": msg.body, "created_at": msg.created_at}
            if msg
            else None
        )


# -------------------------
# Business Logic Serializers
# -------------------------


class CreateConversationSerializer(serializers.Serializer):
    other_user_id = serializers.IntegerField()

    def validate_other_user_id(self, value):
        request = self.context["request"]
        if value == request.user.id:
            raise serializers.ValidationError(
                "Cannot create conversation with yourself."
            )
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        other = User.objects.get(id=validated_data["other_user_id"])

        convo, created = get_or_create_dm(request.user, other)
        self._created_flag = created
        return convo

    @property
    def created_flag(self):
        return getattr(self, "_created_flag", False)


class CreateMessageSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=False, max_length=5000)

    def validate(self, attrs):
        request = self.context["request"]
        convo = self.context.get("conversation")

        if convo is None:
            raise serializers.ValidationError("Conversation context is required.")

        is_member = ConversationMember.objects.filter(
            conversation=convo, user=request.user
        ).exists()
        if not is_member:
            raise serializers.ValidationError(
                "You are not a member of this conversation."
            )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        convo: Conversation = self.context["conversation"]

        msg = Message.objects.create(
            conversation=convo,
            sender=request.user,
            body=validated_data["body"],
        )

        # ✅ A버전 핵심: 대화방 마지막 메시지 시각 갱신
        # updated_at은 auto_now로 자동 갱신됨
        Conversation.objects.filter(id=convo.id).update(last_message_at=msg.created_at)

        return msg


class MarkReadSerializer(serializers.Serializer):
    read_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        request = self.context["request"]
        convo = self.context.get("conversation")

        if convo is None:
            raise serializers.ValidationError("Conversation context is required.")

        is_member = ConversationMember.objects.filter(
            conversation=convo, user=request.user
        ).exists()
        if not is_member:
            raise serializers.ValidationError(
                "You are not a member of this conversation."
            )

        return attrs

    def save(self, **kwargs):
        request = self.context["request"]
        convo = self.context["conversation"]

        read_at = self.validated_data.get("read_at") or timezone.now()

        ConversationMember.objects.filter(conversation=convo, user=request.user).update(
            last_read_at=read_at
        )

        return {"ok": True, "read_at": read_at}
