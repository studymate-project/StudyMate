from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from apps.community.models import DiscussionComment, DiscussionCommentLike
from apps.resources.models import PublicationStatus, Resource, Video


class DiscussionApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="discussion-owner", password="password")
        self.member = User.objects.create_user(username="discussion-member", password="password")
        self.resource = Resource.objects.create(
            title="Discussion resource",
            uploader=self.owner,
            subject="Physics",
            resource_type=Resource.ResourceType.FILE,
            status=PublicationStatus.PUBLISHED,
        )
        self.video = Video.objects.create(
            title="Discussion video",
            uploader=self.owner,
            subject="Physics",
            youtube_video_id="dQw4w9WgXcQ",
            status=PublicationStatus.PUBLISHED,
        )

    def resource_url(self):
        return f"/api/discussion/resources/{self.resource.pk}/"

    def video_url(self):
        return f"/api/discussion/videos/{self.video.slug}/"

    def test_discussion_comments_and_one_level_replies_are_persistent(self):
        anonymous_response = self.client.post(self.resource_url(), {"body": "Anonymous"}, format="json")
        self.assertEqual(anonymous_response.status_code, 401)

        public_response = self.client.get(self.resource_url())
        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(public_response.data["results"], [])

        self.client.force_authenticate(user=self.member)
        comment_response = self.client.post(self.resource_url(), {"body": "Helpful explanation"}, format="json")
        self.assertEqual(comment_response.status_code, 201)
        comment = DiscussionComment.objects.get(pk=comment_response.data["id"])
        self.assertEqual(comment.resource_id, self.resource.pk)
        self.assertIsNone(comment.parent_id)

        reply_response = self.client.post(
            self.resource_url(), {"body": "Thanks for explaining this.", "parent": comment.pk}, format="json"
        )
        self.assertEqual(reply_response.status_code, 201)
        reply = DiscussionComment.objects.get(pk=reply_response.data["id"])
        self.assertEqual(reply.parent_id, comment.pk)

        nested_reply_response = self.client.post(
            self.resource_url(), {"body": "A reply to a reply", "parent": reply.pk}, format="json"
        )
        self.assertEqual(nested_reply_response.status_code, 400)

        list_response = self.client.get(self.resource_url())
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["replies"][0]["id"], reply.pk)

    def test_detail_discussions_support_frontend_paginated_get_for_resources_and_videos(self):
        self.video.slug = "search-audit-video"
        self.video.save(update_fields=("slug",))

        for url in (self.resource_url(), self.video_url()):
            response = self.client.get(url, {"page": 1, "page_size": 100})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 0)
            self.assertEqual(response.data["results"], [])

    def test_comment_likes_are_authenticated_idempotent_and_removable(self):
        self.client.force_authenticate(user=self.member)
        comment_response = self.client.post(self.video_url(), {"body": "Video question"}, format="json")
        self.assertEqual(comment_response.status_code, 201)
        comment_id = comment_response.data["id"]
        like_url = f"/api/discussion/comments/{comment_id}/like/"

        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post(like_url, {}, format="json").status_code, 401)

        self.client.force_authenticate(user=self.member)
        first_like = self.client.post(like_url, {}, format="json")
        duplicate_like = self.client.post(like_url, {}, format="json")
        self.assertEqual(first_like.status_code, 201)
        self.assertEqual(duplicate_like.status_code, 200)
        self.assertEqual(duplicate_like.data["like_count"], 1)
        self.assertEqual(DiscussionCommentLike.objects.filter(comment_id=comment_id).count(), 1)

        unlike = self.client.delete(like_url)
        self.assertEqual(unlike.status_code, 200)
        self.assertEqual(unlike.data["like_count"], 0)
        self.assertFalse(DiscussionCommentLike.objects.filter(comment_id=comment_id).exists())

    def test_replies_cannot_cross_targets_and_blank_comments_are_rejected(self):
        self.client.force_authenticate(user=self.member)
        comment_response = self.client.post(self.resource_url(), {"body": "Resource comment"}, format="json")
        comment_id = comment_response.data["id"]

        cross_target = self.client.post(
            self.video_url(), {"body": "Wrong target", "parent": comment_id}, format="json"
        )
        blank = self.client.post(self.video_url(), {"body": "   "}, format="json")
        self.assertEqual(cross_target.status_code, 400)
        self.assertEqual(blank.status_code, 400)

        video_list = self.client.get(self.video_url())
        self.assertEqual(video_list.status_code, 200)
        self.assertEqual(video_list.data["count"], 0)
