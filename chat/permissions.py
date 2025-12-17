from rest_framework.permissions import BasePermission
from .models import ConversationMember


class IsConversationMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        return ConversationMember.objects.filter(
            conversation=obj, user=request.user
        ).exists()
