from django.test import SimpleTestCase

from .models import Notification
from apps.interactions.models import (
    AnswerUpvote,
    QuestionUpvote,
    ResourceRating,
    ResourceUpvote,
    SavedResource,
    UserFollow,
)
from apps.resources.models import ResourceDownload, ResourceView


def _index_fields(model):
    return {tuple(index.fields): index for index in model._meta.indexes}


class EventAndNotificationIndexContractTests(SimpleTestCase):
    def test_notification_indexes_match_list_and_unread_queries(self):
        indexes = _index_fields(Notification)

        self.assertIn(("recipient", "is_read", "created_at"), indexes)
        self.assertIn(("recipient", "-created_at", "-id"), indexes)
        self.assertIn(("content_type", "object_id"), indexes)

    def test_event_indexes_match_resource_and_user_history_queries(self):
        self.assertIn(("resource", "viewed_at"), _index_fields(ResourceView))
        self.assertIn(("user", "viewed_at"), _index_fields(ResourceView))
        self.assertIn(("resource", "downloaded_at"), _index_fields(ResourceDownload))
        self.assertIn(("user", "downloaded_at"), _index_fields(ResourceDownload))

    def test_relationship_indexes_match_resource_and_user_history_queries(self):
        for model in (
            SavedResource,
            ResourceUpvote,
            QuestionUpvote,
            AnswerUpvote,
        ):
            indexes = _index_fields(model)
            self.assertIn(("user", "created_at"), indexes)
            target_field = {
                SavedResource: "resource",
                ResourceUpvote: "resource",
                QuestionUpvote: "question",
                AnswerUpvote: "answer",
            }[model]
            self.assertIn((target_field, "created_at"), indexes)

        follow_indexes = _index_fields(UserFollow)
        self.assertIn(("follower", "created_at"), follow_indexes)
        self.assertIn(("following", "created_at"), follow_indexes)

    def test_rating_indexes_match_target_aggregation_queries(self):
        indexes = _index_fields(ResourceRating)
        self.assertIn(("resource", "rating"), indexes)
        self.assertIn(("video", "rating"), indexes)
        self.assertIn(("user", "created_at"), indexes)
