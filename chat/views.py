from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import render

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, ConversationMember, Message
from .permissions import IsConversationMember
from .serializers import (
    ConversationListSerializer,
    CreateConversationSerializer,
    CreateMessageSerializer,
    MarkReadSerializer,
    MessageSerializer,
    UserPublicSerializer,
)

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def index(request):
    return render(request, "chat/index.html")


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"ok": True})


class UserSearchAPI(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserPublicSerializer

    def get_queryset(self):
        me = self.request.user
        q = (self.request.query_params.get("query") or "").strip()

        qs = User.objects.exclude(id=me.id).order_by("username")
        if not q:
            return qs.none()

        return qs.filter(Q(username__icontains=q) | Q(email__icontains=q))[:20]


class MessageCursorPagination(CursorPagination):
    page_size = 30
    ordering = "-created_at"


class ConversationListCreateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user

        member_last_read_qs = ConversationMember.objects.filter(
            conversation=OuterRef("pk"), user=me
        ).values("last_read_at")[:1]

        conversations = (
            Conversation.objects.filter(conversationmember__user=me)
            .annotate(my_last_read_at=Subquery(member_last_read_qs))
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=(
                        ~Q(messages__sender=me)
                        & (
                            Q(my_last_read_at__isnull=True)
                            | Q(messages__created_at__gt=Subquery(member_last_read_qs))
                        )
                    ),
                )
            )
            # ✅ A버전 핵심: 마지막 메시지 시각 기준으로 정렬
            .order_by("-last_message_at", "-updated_at", "-created_at")
            .distinct()
        )

        ser = ConversationListSerializer(
            conversations, many=True, context={"request": request}
        )
        return Response(ser.data)

    def post(self, request):
        ser = CreateConversationSerializer(
            data=request.data,
            context={"request": request},
        )
        ser.is_valid(raise_exception=True)

        convo = ser.save()
        created = ser.created_flag

        return Response(
            {"id": convo.id, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationMessagesAPI(APIView):
    permission_classes = [IsAuthenticated, IsConversationMember]

    def _get_conversation(self, request, convo_id):
        convo = Conversation.objects.filter(id=convo_id).first()
        if not convo:
            return None
        self.check_object_permissions(request, convo)
        return convo

    def get(self, request, convo_id):
        convo = self._get_conversation(request, convo_id)
        if not convo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        qs = Message.objects.filter(conversation=convo).order_by("-created_at")

        paginator = MessageCursorPagination()
        page = paginator.paginate_queryset(qs, request)

        data = MessageSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    def post(self, request, convo_id):
        convo = self._get_conversation(request, convo_id)
        if not convo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = CreateMessageSerializer(
            data=request.data,
            context={"request": request, "conversation": convo},
        )
        ser.is_valid(raise_exception=True)

        msg = ser.save()
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class ConversationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated, IsConversationMember]

    def patch(self, request, convo_id):
        convo = Conversation.objects.filter(id=convo_id).first()
        if not convo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, convo)

        ser = MarkReadSerializer(
            data=request.data,
            context={"request": request, "conversation": convo},
        )
        ser.is_valid(raise_exception=True)

        result = ser.save()
        return Response(result)
