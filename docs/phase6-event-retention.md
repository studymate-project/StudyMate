# Phase 6 event durability and retention

This inventory describes the event-like records currently written by StudyMate.
It is intentionally based on the existing models and write paths; it does not
introduce a new event store or move durable history into Redis.

| Record | Purpose | Durable requirement | Current retention / write policy |
| --- | --- | --- | --- |
| `resources.ResourceView` | Resource-view analytics and popularity signals | Keep the raw row in PostgreSQL while the analytics policy requires it | One row per accepted tracking request; repeated requests remain separate events. User is nullable so anonymous and post-account-deletion telemetry can remain. |
| `resources.ResourceDownload` | Resource-download analytics and popularity signals | Keep the raw row in PostgreSQL while the analytics policy requires it | One row per accepted tracking request; repeated downloads remain separate events. |
| `interactions.SavedResource` | Current user save relationship | Durable PostgreSQL state until unsave, resource deletion, or account deletion | Database uniqueness prevents duplicate user/resource relationships. |
| `interactions.ResourceUpvote` | Current resource upvote relationship | Durable PostgreSQL state until removal, resource deletion, or account deletion | Database uniqueness prevents duplicate user/resource relationships. |
| `interactions.ResourceRating` | Current user rating for a resource or video | Durable PostgreSQL state; `updated_at` records changes to the current rating | One unique rating per user/target; updates replace the current value rather than creating an audit history. |
| `interactions.QuestionUpvote` | Current question upvote relationship | Durable PostgreSQL state until removal, question deletion, or account deletion | Database uniqueness prevents duplicate user/question relationships. |
| `interactions.AnswerUpvote` | Current answer upvote relationship | Durable PostgreSQL state until removal, answer deletion, or account deletion | Database uniqueness prevents duplicate user/answer relationships. |
| `interactions.UserFollow` | Current follower relationship | Durable PostgreSQL state until unfollow or account deletion | Database uniqueness prevents duplicate follower/following relationships. |
| `community.Question`, `Answer`, `DiscussionComment` | User-generated study and discussion history | Durable PostgreSQL content; deletion/status rules remain authoritative | No automatic purge or archive task exists. `archived` is a content status, not telemetry retention. |
| `community.DiscussionCommentLike` | Current like relationship on a discussion comment | Durable PostgreSQL state until unlike, comment deletion, or account deletion | Database uniqueness prevents duplicate user/comment likes. |
| `notifications.Notification` | User-visible notification history and read state | Durable PostgreSQL history for the recipient; preserve recipient isolation | No automatic purge/archive mechanism exists. Generic target references may become unavailable after target deletion. |
| `users.SignupEmailVerification` | Current signup verification state and delivery bookkeeping | Pending/unverified rows remain durable while the inactive account may use resend; completed rows remain until an explicitly approved cleanup window | Token material is hashed; verification expiry and single-use state remain authoritative. Only completed rows with `verified_at` set and an empty `otp_hash` can become cleanup candidates after `expires_at` plus the configured post-expiry retention window. Cleanup is disabled by default. |

## Aggregation boundary

Subject recommendations aggregate views, downloads, saves, upvotes, ratings, and
discussion activity in `backend/apps/resources/views.py`. The aggregate is
cached with an existing bounded 5–15 minute TTL. Saves, upvotes, and ratings
still invalidate that cache after commit because they are lower-volume
relationship changes. View/download inserts continue to be written directly to
PostgreSQL, but no longer perform a Redis version write for every telemetry
event; the existing TTL bounds aggregate staleness.

This is not an exact-once or deduplication guarantee. No view/download rows are
deleted or merged, because the current API has no event identifier and the
product has not established that repeated requests represent duplicates rather
than separate analytics events. Any future roll-up or purge must define a
retention window and preserve the required aggregate before deleting raw rows.

## Retention and cleanup policy

The product has not established a raw analytics retention window, and no
user-visible history, notification history, relationship state, content, or
security/audit record is eligible for automatic deletion. Those records remain
in PostgreSQL under their existing lifecycle rules.

Expired but unverified signup records are also retained because the resend
flow uses the existing row. The only cleanup class is completed signup
verification bookkeeping after the OTP hash has already been cleared and the
OTP expiry plus an explicitly configured post-expiry retention window has
elapsed. The cleanup is opt-in (`RETENTION_CLEANUP_ENABLED=False` by default),
so the retention window must be approved and configured by the deployment
operator rather than invented by application defaults.

Cleanup runs use PostgreSQL advisory locking, bounded batches, one database
transaction per batch, optional pacing, and bounded Celery retries. The
management command is dry-run by default:

```text
python manage.py cleanup_retention
python manage.py cleanup_retention --execute
```

Celery Beat remains unconfigured. Production scheduling requires a separate,
deployment-approved scheduler or cron job to invoke the explicit command or
enqueue `apps.users.tasks.cleanup_expired_signup_verifications_task`; configure
only one scheduler or rely on the database advisory lock for overlapping
invocations. Successful runs emit privacy-safe structured logs containing
duration, processed/deleted counts, batch count, and the last successful run
timestamp. No production cleanup is performed by development or test runs.
