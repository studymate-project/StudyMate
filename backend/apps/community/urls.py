from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AnswerCreateView, AnswerDetailView, AnswerUpvoteView, ProfileAnswerListView, QuestionUpvoteView, QuestionViewSet


router = DefaultRouter()
router.register(r"", QuestionViewSet, basename="question")

urlpatterns = [
    path("answers/", ProfileAnswerListView.as_view(), name="profile-answers"),
    path("<int:question_id>/upvote/", QuestionUpvoteView.as_view(), name="question-upvote"),
    path("<int:question_id>/answers/", AnswerCreateView.as_view(), name="question-answers"),
    path(
        "<int:question_id>/answers/<int:answer_id>/upvote/",
        AnswerUpvoteView.as_view(),
        name="answer-upvote",
    ),
    path(
        "<int:question_id>/answers/<int:pk>/",
        AnswerDetailView.as_view(),
        name="question-answer-detail",
    ),
    *router.urls,
]
