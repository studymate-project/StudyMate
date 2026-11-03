# Celery-independent critical-path audit update

## Change made

Email verification is now opt-in through
`SIGNUP_EMAIL_VERIFICATION_REQUIRED`, which defaults to `False`.

## Files affected

- `backend/backend/settings.py` — added the feature flag.
- `backend/apps/users/serializers.py` — new users are active immediately when
  verification is not required; verification state is still created through
  the existing path when the flag is enabled.
- `backend/apps/core/views.py` — signup responses expose
  `verification_required` so the client can select the correct flow.
- `frontend/src/pages/Signup.jsx` — default signup completes by sending the
  user to login; the existing OTP UI remains available when the backend
  explicitly requires verification.
- `backend/.env.example` and `backend/README.md` — documented the deployment
  setting and worker/email requirement for the opt-in mode.

## Why

The prior default created an inactive account and queued a Celery email task
inside the signup transaction's `on_commit` callback. Without a worker, the
task could be queued but never processed, leaving the new account unable to
log in. The default now completes user/profile persistence synchronously and
does not enqueue an unnecessary email task. The existing email task,
verification endpoints, retry behavior, and security validation remain intact
for a future deployment that intentionally enables verification.

This does not remove the production Redis requirement for throttling/cache, or
the synchronous Cloudinary dependency for file uploads. It only removes the
unneeded worker dependency from the current signup critical path.
