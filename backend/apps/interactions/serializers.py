from rest_framework import serializers

from apps.community.models import Answer, Question
from apps.resources.models import Resource
from apps.users.serializers import PublicUserSerializer

from .models import AnswerUpvote, QuestionUpvote, ResourceUpvote, SavedResource


class ResourceReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ("id", "title", "slug")
        read_only_fields = fields


class QuestionReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ("id", "title", "slug", "subject")
        read_only_fields = fields


class AnswerReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ("id", "question", "author", "is_helpful")
        read_only_fields = fields


class SavedResourceSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    resource_detail = ResourceReferenceSerializer(source="resource", read_only=True)

    class Meta:
        model = SavedResource
        fields = ("id", "user", "resource", "resource_detail", "created_at")
        read_only_fields = ("id", "user", "resource_detail", "created_at")


class ResourceUpvoteSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    resource_detail = ResourceReferenceSerializer(source="resource", read_only=True)

    class Meta:
        model = ResourceUpvote
        fields = ("id", "user", "resource", "resource_detail", "created_at")
        read_only_fields = ("id", "user", "resource_detail", "created_at")


class QuestionUpvoteSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    question_detail = QuestionReferenceSerializer(source="question", read_only=True)

    class Meta:
        model = QuestionUpvote
        fields = ("id", "user", "question", "question_detail", "created_at")
        read_only_fields = ("id", "user", "question_detail", "created_at")


class AnswerUpvoteSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    answer_detail = AnswerReferenceSerializer(source="answer", read_only=True)

    class Meta:
        model = AnswerUpvote
        fields = ("id", "user", "answer", "answer_detail", "created_at")
        read_only_fields = ("id", "user", "answer_detail", "created_at")
