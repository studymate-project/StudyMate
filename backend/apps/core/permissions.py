"""Reusable object-level permissions for StudyMate-owned domain objects."""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsOwnerOrReadOnly(BasePermission):
    """Allow public safe reads and restrict mutations to an object's owner."""

    owner_attribute = ""

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, self.owner_attribute, None)
        return bool(request.user.is_authenticated and owner == request.user)


class IsProfileOwnerOrReadOnly(IsOwnerOrReadOnly):
    owner_attribute = "user"


class IsResourceOwnerOrReadOnly(IsOwnerOrReadOnly):
    owner_attribute = "uploader"


class IsVideoOwnerOrReadOnly(IsOwnerOrReadOnly):
    owner_attribute = "uploader"


class IsQuestionAuthorOrReadOnly(IsOwnerOrReadOnly):
    owner_attribute = "author"


class IsAnswerAuthorOrReadOnly(IsOwnerOrReadOnly):
    owner_attribute = "author"


class IsDiscussionCommentAuthorOrReadOnly(IsOwnerOrReadOnly):
    owner_attribute = "author"


class IsNotificationRecipient(IsOwnerOrReadOnly):
    owner_attribute = "recipient"
