import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("community", "0005_search_indexes"),
        ("resources", "0007_search_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiscussionComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(max_length=10000)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending", "Pending review"),
                            ("published", "Published"),
                            ("rejected", "Rejected"),
                            ("archived", "Archived"),
                        ],
                        db_index=True,
                        default="published",
                        max_length=12,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="discussion_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="replies",
                        to="community.discussioncomment",
                    ),
                ),
                (
                    "resource",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discussion_comments",
                        to="resources.resource",
                    ),
                ),
                (
                    "video",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discussion_comments",
                        to="resources.video",
                    ),
                ),
            ],
            options={
                "ordering": ("created_at", "pk"),
                "indexes": [
                    models.Index(fields=["resource", "parent", "created_at"], name="community_d_resourc_478f3f_idx"),
                    models.Index(fields=["video", "parent", "created_at"], name="community_d_video_i_e0b2f1_idx"),
                    models.Index(fields=["author", "created_at"], name="community_d_author__f70696_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="DiscussionCommentLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "comment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="community.discussioncomment",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discussion_comment_likes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user", "created_at"], name="community_d_user_id_b07716_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="discussioncomment",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("resource__isnull", False), ("video__isnull", True))
                    | models.Q(("resource__isnull", True), ("video__isnull", False))
                ),
                name="community_discussion_one_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="discussioncommentlike",
            constraint=models.UniqueConstraint(
                fields=("comment", "user"),
                name="community_discussion_like_unique",
            ),
        ),
    ]
