from rest_framework import serializers
from django.db import transaction
from django.utils.text import slugify

from apps.resources.models import Tag
from apps.resources.serializers import TagSerializer
from apps.users.serializers import PublicUserSerializer

from .models import Answer, Question


class QuestionSerializer(serializers.ModelSerializer):
    author = PublicUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    upvotes = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags", many=True, queryset=Tag.objects.all(), write_only=True, required=False
    )
    tag_names = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=500)

    class Meta:
        model = Question
        fields = (
            "id",
            "title",
            "slug",
            "body",
            "author",
            "subject",
            "topic",
            "academic_level",
            "tags",
            "tag_ids",
            "tag_names",
            "upvotes",
            "answers",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "author", "status", "created_at", "updated_at")

    def get_upvotes(self, question: Question) -> int:
        if hasattr(question, "upvotes_count"):
            return question.upvotes_count
        return question.upvotes.count()

    def get_answers(self, question: Question) -> int:
        if hasattr(question, "answers_count"):
            return question.answers_count
        return question.answers.count()

    @staticmethod
    def _tag_names(value):
        if not value:
            return []
        return list(dict.fromkeys(name.strip().lstrip('#') for name in value.split(',') if name.strip()))

    def _save_tag_names(self, question, value):
        names = self._tag_names(value)
        if not names:
            return

        tags = []
        for name in names:
            tag, _ = Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})
            tags.append(tag)
        question.tags.set(tags)

    @transaction.atomic
    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", "")
        question = super().create(validated_data)
        self._save_tag_names(question, tag_names)
        return question

    @transaction.atomic
    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        question = super().update(instance, validated_data)
        if tag_names is not None:
            self._save_tag_names(question, tag_names)
        return question


class AnswerSerializer(serializers.ModelSerializer):
    author = PublicUserSerializer(read_only=True)
    upvotes = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = ("id", "question", "author", "body", "is_helpful", "upvotes", "status", "created_at", "updated_at")
        read_only_fields = ("id", "question", "author", "is_helpful", "status", "created_at", "updated_at")

    def get_upvotes(self, answer: Answer) -> int:
        upvotes_count = getattr(answer, "upvotes_count", None)
        return upvotes_count if upvotes_count is not None else answer.upvotes.count()


class ProfileAnswerSerializer(AnswerSerializer):
    question_title = serializers.CharField(source="question.title", read_only=True)
    question_slug = serializers.CharField(source="question.slug", read_only=True)

    class Meta(AnswerSerializer.Meta):
        fields = AnswerSerializer.Meta.fields + ("question_title", "question_slug")
