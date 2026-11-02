from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserBlock


class UserBlockListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        blocks = (
            UserBlock.objects.filter(blocker=request.user)
            .select_related("blocked")
            .order_by("-created_at", "-id")
        )
        return Response(
            {
                "blocked_users": [
                    {
                        "id": block.blocked_id,
                        "username": block.blocked.username,
                        "blocked_at": block.created_at,
                    }
                    for block in blocks
                ]
            }
        )

    def post(self, request):
        user_id = request.data.get("user_id")
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "A user id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user_id == request.user.id:
            return Response(
                {"detail": "You cannot block yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        blocked = User.objects.filter(pk=user_id).first()
        if blocked is None:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if UserBlock.objects.filter(blocker=request.user, blocked=blocked).exists():
            return Response(
                {"detail": "You have already blocked this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            with transaction.atomic():
                block = UserBlock.objects.create(blocker=request.user, blocked=blocked)
        except IntegrityError:
            return Response(
                {"detail": "You have already blocked this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "id": block.blocked_id,
                "username": block.blocked.username,
                "blocked_at": block.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class UserUnblockView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        deleted, _ = UserBlock.objects.filter(
            blocker=request.user,
            blocked_id=user_id,
        ).delete()
        if not deleted:
            return Response({"detail": "Block not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
