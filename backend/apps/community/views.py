import logging

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers
from rest_framework.generics import CreateAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.core.permissions import IsAnswerAuthorOrReadOnly, IsQuestionAuthorOrReadOnly
from apps.core.schema import BAD_REQUEST, FORBIDDEN, NOT_FOUND, UNAUTHENTICATED

from apps.resources.models import PublicationStatus

from apps.interactions.models import AnswerUpvote, QuestionUpvote
from apps.notifications.models import Notification
from apps.notifications.services import create_notification

from .models import Answer, Question
from .serializers import AnswerSerializer, ProfileAnswerSerializer, QuestionSerializer


QUESTION_UPVOTE_RESPONSE = inline_serializer(
    "QuestionUpvoteResponse",
    fields={
        "upvoted": serializers.BooleanField(read_only=True),
        "question": serializers.IntegerField(read_only=True),
        "upvotes": serializers.IntegerField(read_only=True),
    },
)
ANSWER_UPVOTE_RESPONSE = inline_serializer(
    "AnswerUpvoteResponse",
    fields={
        "upvoted": serializers.BooleanField(read_only=True),
        "answer": serializers.IntegerField(read_only=True),
        "upvotes": serializers.IntegerField(read_only=True),
    },
)


logger = logging.getLogger(__name__)


def visible_question_queryset(request):
    questions = Question.objects.all()
    if request.user.is_authenticated:
        return questions.filter(Q(status=PublicationStatus.PUBLISHED) | Q(author=request.user))
    return questions.filter(status=PublicationStatus.PUBLISHED)


def get_visible_question(request, question_id):
    return get_object_or_404(visible_question_queryset(request), pk=question_id)


def visible_answer_queryset(request, question_id):
    question = get_visible_question(request, question_id)
    answers = Answer.objects.select_related("question", "author").annotate(
        upvotes_count=Count("upvotes")
    ).filter(question_id=question.pk).order_by("created_at", "pk")
    if request.user.is_authenticated:
        return answers.filter(
            (Q(question__status=PublicationStatus.PUBLISHED) | Q(question__author=request.user))
            & (Q(status=PublicationStatus.PUBLISHED) | Q(author=request.user))
        )
    return answers.filter(
        question__status=PublicationStatus.PUBLISHED,
        status=PublicationStatus.PUBLISHED,
    )


@extend_schema_view(
    list=extend_schema(
        summary="List questions",
        responses=QuestionSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get a question",
        responses={200: QuestionSerializer, 404: NOT_FOUND},
    ),
    create=extend_schema(
        summary="Create a question",
        description="The server assigns the authenticated author; client input cannot reassign ownership or counters.",
        request=QuestionSerializer,
        responses={201: QuestionSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED},
    ),
    update=extend_schema(
        summary="Replace a question",
        request=QuestionSerializer,
        responses={200: QuestionSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
    partial_update=extend_schema(
        summary="Update a question",
        request=QuestionSerializer,
        responses={200: QuestionSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
    destroy=extend_schema(
        summary="Delete a question",
        responses={204: None, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
)
class QuestionViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = QuestionSerializer
    permission_classes = (IsQuestionAuthorOrReadOnly,)
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_throttles(self):
        self.throttle_scope = "question_write" if self.action == "create" else None
        return super().get_throttles()

    def get_queryset(self):
        queryset = Question.objects.select_related("author", "academic_level").prefetch_related("tags").annotate(
            upvotes_count=Count("upvotes", distinct=True),
            answers_count=Count("answers", distinct=True),
        )
        if self.request.user.is_authenticated:
            return queryset.filter(Q(status=PublicationStatus.PUBLISHED) | Q(author=self.request.user))
        return queryset.filter(status=PublicationStatus.PUBLISHED)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        author = self.request.query_params.get("author")
        if author is not None:
            try:
                author_id = int(author)
            except (TypeError, ValueError):
                return queryset.none()
            if author_id < 1:
                return queryset.none()
            queryset = queryset.filter(author_id=author_id)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(body__icontains=search)
                | Q(subject__icontains=search)
                | Q(topic__icontains=search)
                | Q(tags__name__icontains=search)
            ).distinct()
        return queryset

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsQuestionAuthorOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


@extend_schema(
    operation_id="profile_answers_list",
    summary="List the authenticated user's answers",
    responses=ProfileAnswerSerializer(many=True),
)
class ProfileAnswerListView(ListAPIView):
    """Return one bounded, ownership-scoped answer feed for the profile page."""

    serializer_class = ProfileAnswerSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Answer.objects.select_related("question", "author").annotate(
            upvotes_count=Count("upvotes")
        ).filter(
            author=self.request.user,
        ).filter(
            Q(question__status=PublicationStatus.PUBLISHED) | Q(question__author=self.request.user),
            Q(status=PublicationStatus.PUBLISHED) | Q(author=self.request.user),
        ).order_by("-created_at", "-pk")


@extend_schema_view(
    get=extend_schema(
        summary="List answers for a question",
        responses={200: AnswerSerializer(many=True), 404: NOT_FOUND},
    ),
    post=extend_schema(
        summary="Create an answer",
        description="The server assigns the authenticated author and target question; answering a question triggers the existing notification behavior.",
        request=AnswerSerializer,
        responses={201: AnswerSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    ),
)
class AnswerCreateView(ListCreateAPIView):
    serializer_class = AnswerSerializer
    permission_classes = (IsAuthenticated, IsAnswerAuthorOrReadOnly)

    def get_throttles(self):
        self.throttle_scope = "answer_write" if self.request.method == "POST" else None
        return super().get_throttles()

    def get_queryset(self):
        return visible_answer_queryset(self.request, self.kwargs["question_id"])

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAuthenticated(), IsAnswerAuthorOrReadOnly()]

    def perform_create(self, serializer):
        question = get_visible_question(self.request, self.kwargs["question_id"])
        answer = serializer.save(question=question, author=self.request.user)
        if answer.author_id == question.author_id:
            return

        try:
            create_notification(
                recipient=question.author,
                actor=answer.author,
                notification_type=Notification.NotificationType.QUESTION_ANSWERED,
                related_object=question,
                payload={"answer_id": answer.pk},
            )
        except Exception:
            logger.exception(
                "Unable to create answer notification for question %s after answer %s was created.",
                question.pk,
                answer.pk,
            )


@extend_schema_view(
    get=extend_schema(
        summary="Get an answer",
        responses={200: AnswerSerializer, 404: NOT_FOUND},
    ),
    put=extend_schema(
        summary="Replace an answer",
        request=AnswerSerializer,
        responses={200: AnswerSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
    patch=extend_schema(
        summary="Update an answer",
        request=AnswerSerializer,
        responses={200: AnswerSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
    delete=extend_schema(
        summary="Delete an answer",
        responses={204: None, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
)
class AnswerDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = AnswerSerializer
    permission_classes = (IsAnswerAuthorOrReadOnly,)

    def get_throttles(self):
        self.throttle_scope = "answer_write" if self.request.method not in SAFE_METHODS else None
        return super().get_throttles()

    def get_queryset(self):
        return visible_answer_queryset(self.request, self.kwargs["question_id"])

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAuthenticated(), IsAnswerAuthorOrReadOnly()]


class CommunityUpvoteView(CreateAPIView):
    """Base implementation for idempotent relationship-backed upvotes."""

    permission_classes = (IsAuthenticated,)
    throttle_scope = "interaction_write"
    upvote_model = None
    target_field = ""

    def get_target(self):
        raise NotImplementedError

    @extend_schema(
        summary="Upvote a community object",
        request=None,
        responses={201: QUESTION_UPVOTE_RESPONSE, 200: QUESTION_UPVOTE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def post(self, request, *args, **kwargs):
        target = self.get_target()
        _, created = self.upvote_model.objects.get_or_create(
            user=request.user,
            **{self.target_field: target},
        )
        return Response(
            {
                "upvoted": True,
                self.target_field: target.pk,
                "upvotes": self.upvote_model.objects.filter(**{self.target_field: target}).count(),
            },
            status=201 if created else 200,
        )

    @extend_schema(
        summary="Remove a community upvote",
        request=None,
        responses={200: QUESTION_UPVOTE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def delete(self, request, *args, **kwargs):
        target = self.get_target()
        self.upvote_model.objects.filter(user=request.user, **{self.target_field: target}).delete()
        return Response(
            {
                "upvoted": False,
                self.target_field: target.pk,
                "upvotes": self.upvote_model.objects.filter(**{self.target_field: target}).count(),
            },
            status=200,
        )


@extend_schema_view(
    post=extend_schema(
        summary="Upvote a question",
        request=None,
        responses={201: QUESTION_UPVOTE_RESPONSE, 200: QUESTION_UPVOTE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    ),
    delete=extend_schema(
        summary="Remove a question upvote",
        request=None,
        responses={200: QUESTION_UPVOTE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    ),
)
class QuestionUpvoteView(CommunityUpvoteView):
    upvote_model = QuestionUpvote
    target_field = "question"

    def get_target(self):
        questions = Question.objects.filter(status=PublicationStatus.PUBLISHED)
        if self.request.user.is_authenticated:
            questions = Question.objects.filter(
                Q(status=PublicationStatus.PUBLISHED) | Q(author=self.request.user)
            )
        return get_object_or_404(questions, pk=self.kwargs["question_id"])


@extend_schema_view(
    post=extend_schema(
        summary="Upvote an answer",
        request=None,
        responses={201: ANSWER_UPVOTE_RESPONSE, 200: ANSWER_UPVOTE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    ),
    delete=extend_schema(
        summary="Remove an answer upvote",
        request=None,
        responses={200: ANSWER_UPVOTE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    ),
)
class AnswerUpvoteView(CommunityUpvoteView):
    upvote_model = AnswerUpvote
    target_field = "answer"

    def get_target(self):
        answers = visible_answer_queryset(self.request, self.kwargs["question_id"])
        return get_object_or_404(answers, pk=self.kwargs["answer_id"])
