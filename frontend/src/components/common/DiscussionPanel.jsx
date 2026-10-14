import { MessageSquare, Send, UserRound } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../../api'
import {
  createResourceDiscussionComment,
  createVideoDiscussionComment,
  likeDiscussionComment,
  listResourceDiscussion,
  listVideoDiscussion,
  unlikeDiscussionComment,
} from '../../api/discussions'
import Spinner from './Spinner'

function Avatar() {
  return (
    <span
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-primary-light)]"
      aria-hidden="true"
    >
      <UserRound size={18} />
    </span>
  )
}

function authorName(author) {
  return author?.name || author?.username || 'StudyMate member'
}

function updateComment(comments, commentId, updater) {
  return comments.map((comment) => {
    if (comment.id === commentId) return updater(comment)
    if (!comment.replies?.length) return comment
    const hasReply = comment.replies.some((reply) => reply.id === commentId)
    return hasReply
      ? { ...comment, replies: comment.replies.map((reply) => reply.id === commentId ? updater(reply) : reply) }
      : comment
  })
}

function DiscussionMessage({ comment, onLike, onReply, pendingLikeId, isAuthenticated, onAuthRequired, isReply = false }) {
  const likedLabel = comment.liked ? 'Liked' : 'Like'

  return (
    <article className={`flex min-w-0 gap-3 px-2 py-1 ${isReply ? 'ml-8 sm:ml-12' : ''}`}>
      <Avatar />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <h3 className="text-sm font-semibold text-white">{authorName(comment.author)}</h3>
          <time className="text-xs font-medium text-[var(--color-text)]">{comment.createdAt}</time>
        </div>
        <p className="mt-1 break-words whitespace-pre-wrap text-sm font-medium leading-relaxed text-white/90">{comment.body}</p>
        <div className="mt-2 flex items-center gap-4 text-xs font-semibold text-[var(--color-text)]">
          <button
            type="button"
            aria-pressed={comment.liked}
            disabled={pendingLikeId === comment.id}
            onClick={() => (isAuthenticated ? onLike(comment) : onAuthRequired())}
            className={`rounded px-1 py-1 text-left transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] disabled:cursor-wait disabled:opacity-60 ${comment.liked ? 'text-[var(--color-primary-light)]' : ''}`}
          >
            {pendingLikeId === comment.id ? 'Saving…' : `${likedLabel} (${comment.likeCount})`}
          </button>
          {!isReply ? (
            <button
              type="button"
              onClick={() => (isAuthenticated ? onReply(comment.id) : onAuthRequired())}
              className="rounded px-1 py-1 text-left transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
            >
              Reply
            </button>
          ) : null}
        </div>
      </div>
    </article>
  )
}

function DiscussionPanel({ itemLabel = 'this item', targetType, targetId, targetSlug, authStatus }) {
  const [isOpen, setIsOpen] = useState(false)
  const [comments, setComments] = useState([])
  const [loadState, setLoadState] = useState({ status: 'idle', error: null })
  const [draft, setDraft] = useState('')
  const [replyTargetId, setReplyTargetId] = useState(null)
  const [replyDraft, setReplyDraft] = useState('')
  const [submissionState, setSubmissionState] = useState({ status: 'idle', error: '' })
  const [pendingLikeId, setPendingLikeId] = useState(null)
  const [authNotice, setAuthNotice] = useState('')
  const composerRef = useRef(null)
  const target = targetType === 'resource' ? targetId : targetSlug
  const isAuthenticated = authStatus === 'authenticated'

  useEffect(() => {
    if (!isOpen || loadState.status !== 'loading' || target === null || target === undefined || target === '') return undefined

    let active = true
    const request = targetType === 'resource' ? listResourceDiscussion(target) : listVideoDiscussion(target)
    request.then(
      (nextComments) => {
        if (active) {
          setComments(nextComments)
          setLoadState({ status: 'success', error: null })
        }
      },
      (error) => {
        if (active) setLoadState({ status: 'error', error })
      },
    )

    return () => {
      active = false
    }
  }, [isOpen, loadState.status, target, targetType])

  useEffect(() => {
    if (isOpen && !replyTargetId) composerRef.current?.focus()
  }, [isOpen, replyTargetId])

  const requireAuth = () => {
    setAuthNotice('Please sign in to like, reply, or post in this discussion.')
  }

  const handleLike = async (comment) => {
    setAuthNotice('')
    setPendingLikeId(comment.id)
    try {
      const result = comment.liked
        ? await unlikeDiscussionComment(comment.id)
        : await likeDiscussionComment(comment.id)
      setComments((current) => updateComment(current, comment.id, (item) => ({
        ...item,
        liked: Boolean(result.liked),
        likeCount: result.like_count ?? item.likeCount,
      })))
    } catch (error) {
      setSubmissionState({ status: 'error', error: getApiErrorMessage(error) })
    } finally {
      setPendingLikeId(null)
    }
  }

  const handleReply = (commentId) => {
    setAuthNotice('')
    setReplyTargetId(commentId)
  }

  const handlePost = async (event) => {
    event.preventDefault()
    const body = draft.trim()
    if (!body || !isAuthenticated || submissionState.status === 'loading') return

    setSubmissionState({ status: 'loading', error: '' })
    try {
      const comment = targetType === 'resource'
        ? await createResourceDiscussionComment(target, body)
        : await createVideoDiscussionComment(target, body)
      setComments((current) => [...current, comment])
      setDraft('')
      setSubmissionState({ status: 'success', error: '' })
    } catch (error) {
      setSubmissionState({ status: 'error', error: getApiErrorMessage(error) })
    }
  }

  const handleComposerKeyDown = (event) => {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return

    event.preventDefault()
    if (!draft.trim() || submissionState.status === 'loading') return
    event.currentTarget.form?.requestSubmit()
  }

  const handleReplySubmit = async (event) => {
    event.preventDefault()
    const body = replyDraft.trim()
    if (!body || !replyTargetId || !isAuthenticated || submissionState.status === 'loading') return

    setSubmissionState({ status: 'loading', error: '' })
    try {
      const reply = targetType === 'resource'
        ? await createResourceDiscussionComment(target, body, replyTargetId)
        : await createVideoDiscussionComment(target, body, replyTargetId)
      setComments((current) => updateComment(current, replyTargetId, (comment) => ({
        ...comment,
        replies: [...(comment.replies || []), reply],
      })))
      setReplyDraft('')
      setReplyTargetId(null)
      setSubmissionState({ status: 'success', error: '' })
    } catch (error) {
      setSubmissionState({ status: 'error', error: getApiErrorMessage(error) })
    }
  }

  const handleReplyKeyDown = (event) => {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return

    event.preventDefault()
    if (!replyDraft.trim() || submissionState.status === 'loading') return
    event.currentTarget.form?.requestSubmit()
  }

  const retry = () => setLoadState({ status: 'loading', error: null })
  const toggleChat = () => {
    if (!isOpen && loadState.status === 'idle') setLoadState({ status: 'loading', error: null })
    setIsOpen((value) => !value)
  }

  return (
    <section className="min-w-0 overflow-hidden py-5" aria-labelledby="discussion-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="discussion-heading" className="text-base font-semibold text-white">Discussion</h2>
          {!isOpen ? <p className="mt-1 text-sm font-medium text-[var(--color-text)]">Ask questions and share helpful explanations about {itemLabel}.</p> : null}
        </div>
        <button
          type="button"
          aria-expanded={isOpen}
          aria-controls="discussion-chat"
          onClick={toggleChat}
          className="inline-flex min-h-10 items-center gap-2 rounded-lg px-2 text-sm font-semibold text-[var(--color-primary-light)] transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
        >
          <MessageSquare size={17} aria-hidden="true" />
          {isOpen ? 'Close chat' : 'View chat'}
        </button>
      </div>

      {isOpen ? (
        <div id="discussion-chat" className="mt-4 flex max-h-[min(36rem,70vh)] min-h-[18rem] flex-col overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]">
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-[var(--color-surface)] px-1 py-3 sm:px-2" aria-live="polite">
            {loadState.status === 'loading' ? (
              <div className="flex justify-center py-10"><Spinner label="Loading discussion" /></div>
            ) : loadState.status === 'error' ? (
              <div className="px-2 py-8 text-center text-sm font-medium text-[var(--color-danger)]">
                <p>{getApiErrorMessage(loadState.error)}</p>
                <button type="button" onClick={retry} className="mt-3 text-[var(--color-primary-light)] underline underline-offset-4">Try again</button>
              </div>
            ) : comments.length ? (
              <div className="space-y-6">
                {comments.map((comment) => (
                  <div key={comment.id}>
                    <DiscussionMessage
                      comment={comment}
                      onLike={handleLike}
                      onReply={handleReply}
                      pendingLikeId={pendingLikeId}
                      isAuthenticated={isAuthenticated}
                      onAuthRequired={requireAuth}
                    />
                    {replyTargetId === comment.id ? (
                      <form onSubmit={handleReplySubmit} className="ml-14 mt-3 flex max-w-[calc(100%-3.5rem)] items-end gap-2 sm:ml-20">
                        <label htmlFor={`reply-${comment.id}`} className="sr-only">Reply to {authorName(comment.author)}</label>
                        <textarea
                          id={`reply-${comment.id}`}
                          value={replyDraft}
                          onChange={(event) => setReplyDraft(event.target.value)}
                          onKeyDown={handleReplyKeyDown}
                          placeholder="Write a helpful reply..."
                          rows={2}
                          className="min-h-11 min-w-0 flex-1 resize-none rounded-2xl border border-[var(--color-border-strong)] bg-[var(--color-band)] px-4 py-2 text-sm font-medium text-white outline-none placeholder:text-[var(--color-text)] focus:border-[var(--color-primary-light)] focus:ring-2 focus:ring-[var(--color-primary-light)]/30"
                        />
                        <button type="submit" disabled={!replyDraft.trim() || submissionState.status === 'loading'} className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary)] p-0 text-[var(--color-bg)] transition-colors hover:bg-[var(--color-primary-light)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] disabled:cursor-not-allowed disabled:opacity-50" aria-label="Send reply" title="Send reply">
                          <Send size={16} aria-hidden="true" />
                        </button>
                        <button type="button" onClick={() => setReplyTargetId(null)} className="self-center px-1 text-xs font-semibold text-[var(--color-text)] hover:text-white">Cancel</button>
                      </form>
                    ) : null}
                    {comment.replies?.length ? (
                      <div className="mt-4 space-y-4">
                        {comment.replies.map((reply) => (
                          <DiscussionMessage
                            key={reply.id}
                            comment={reply}
                            onLike={handleLike}
                            pendingLikeId={pendingLikeId}
                            isAuthenticated={isAuthenticated}
                            onAuthRequired={requireAuth}
                            isReply
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="px-2 py-8 text-center text-sm font-medium text-[var(--color-text)]">No messages yet. Start the conversation.</p>
            )}
          </div>

          <div className="shrink-0 border-t border-[var(--color-border)] bg-[var(--color-surface)] px-2 pb-2 pt-3 sm:px-3">
            {authNotice ? <p className="mb-2 px-1 text-sm font-medium text-[var(--color-primary-light)]" role="status">{authNotice} <Link className="underline underline-offset-4" to="/login">Sign in</Link></p> : null}
            {submissionState.status === 'error' ? <p className="mb-2 px-1 text-sm font-medium text-[var(--color-danger)]" role="alert">{submissionState.error}</p> : null}
            {submissionState.status === 'success' ? <p className="mb-2 px-1 text-sm font-medium text-[var(--color-success)]" role="status">Your message was posted.</p> : null}
            {isAuthenticated ? (
              <form onSubmit={handlePost}>
                <label htmlFor="discussion-message" className="sr-only">Message</label>
                <div className="flex min-w-0 items-end gap-2">
                  <textarea
                    ref={composerRef}
                    id="discussion-message"
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={handleComposerKeyDown}
                    placeholder="Join the discussion..."
                    rows={2}
                    disabled={submissionState.status === 'loading'}
                    className="min-h-12 min-w-0 flex-1 resize-none rounded-2xl border border-[var(--color-border-strong)] bg-[var(--color-band)] px-4 py-3 text-sm font-medium text-white outline-none placeholder:text-[var(--color-text)] focus:border-[var(--color-primary-light)] focus:ring-2 focus:ring-[var(--color-primary-light)]/30 disabled:opacity-60"
                  />
                  <button type="submit" disabled={!draft.trim() || submissionState.status === 'loading'} className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary)] p-0 text-[var(--color-bg)] transition-colors hover:bg-[var(--color-primary-light)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] disabled:cursor-not-allowed disabled:opacity-50" aria-label="Post message" title="Post message">
                    <Send size={16} aria-hidden="true" />
                    <span className="sr-only">{submissionState.status === 'loading' ? 'Posting…' : 'Post'}</span>
                  </button>
                </div>
              </form>
            ) : (
              <p className="px-1 text-sm font-medium text-[var(--color-text)]">Sign in to join the discussion. <Link className="text-[var(--color-primary-light)] underline underline-offset-4" to="/login">Sign in</Link></p>
            )}
          </div>
        </div>
      ) : null}
    </section>
  )
}

export default DiscussionPanel
