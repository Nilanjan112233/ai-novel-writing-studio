'use client'

/**
 * CommentsPanel — Phase 5B
 *
 * Inline comments & review workflow for a paragraph.
 * - Add comments
 * - Reply to threads
 * - Resolve / reopen
 * - Status filter (all / open / resolved)
 * - Reviewer metadata
 */

import { useEffect, useRef, useState } from 'react'
import {
  MessageSquare,
  Send,
  CheckCircle,
  RefreshCw,
  Loader2,
  CornerDownRight,
  MessageCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/store/projectStore'
import type { ParagraphComment } from '@/types'

// ── Utilities ─────────────────────────────────────────────────────────────

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

// ── Thread component ───────────────────────────────────────────────────────

interface ThreadProps {
  comment: ParagraphComment
  projectId: string
  sceneId: string
  onResolve: () => void
  onReply: (content: string) => void
}

function CommentThread({ comment, onResolve, onReply }: ThreadProps) {
  const [showReply, setShowReply] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [isSending, setIsSending] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const handleSendReply = async () => {
    if (!replyText.trim()) return
    setIsSending(true)
    try {
      await onReply(replyText.trim())
      setReplyText('')
      setShowReply(false)
    } finally {
      setIsSending(false)
    }
  }

  const isResolved = comment.status === 'resolved'

  return (
    <div
      className={`rounded-lg border transition-colors ${
        isResolved ? 'bg-muted/10 border-dashed opacity-60' : 'bg-background border-border'
      }`}
    >
      {/* Root comment */}
      <div className="p-3">
        <div className="flex items-start gap-2">
          {/* Avatar */}
          <div className="h-6 w-6 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 mt-0.5">
            <span className="text-[9px] font-bold text-primary uppercase">
              {comment.author.charAt(0)}
            </span>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-[11px] font-bold text-foreground">{comment.author}</span>
              <span className="text-[10px] text-muted-foreground">{formatTime(comment.created_at)}</span>
              {isResolved && (
                <span className="ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 border border-emerald-200">
                  resolved
                </span>
              )}
            </div>
            <p className="text-[12px] text-foreground leading-relaxed">{comment.content}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 mt-2 ml-8">
          {!isResolved && (
            <>
              <Button
                size="sm"
                variant="ghost"
                className="h-5 px-2 text-[10px] gap-1 text-muted-foreground hover:text-foreground"
                onClick={() => {
                  setShowReply(!showReply)
                  setTimeout(() => inputRef.current?.focus(), 50)
                }}
              >
                <CornerDownRight className="h-3 w-3" />
                Reply
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-5 px-2 text-[10px] gap-1 text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50"
                onClick={onResolve}
              >
                <CheckCircle className="h-3 w-3" />
                Resolve
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="border-t ml-6 divide-y">
          {comment.replies.map((reply) => (
            <div key={reply.reply_id} className="px-3 py-2">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="h-4 w-4 rounded-full bg-muted border flex items-center justify-center shrink-0">
                  <span className="text-[8px] font-bold text-muted-foreground uppercase">
                    {reply.author.charAt(0)}
                  </span>
                </div>
                <span className="text-[11px] font-semibold text-foreground">{reply.author}</span>
                <span className="text-[10px] text-muted-foreground">{formatTime(reply.created_at)}</span>
              </div>
              <p className="text-[12px] text-foreground leading-relaxed ml-5">{reply.content}</p>
            </div>
          ))}
        </div>
      )}

      {/* Reply input */}
      {showReply && !isResolved && (
        <div className="border-t px-3 py-2 ml-6 flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Write a reply…"
            rows={2}
            className="flex-1 text-[12px] resize-none border rounded px-2 py-1.5 bg-background focus:outline-none focus:ring-1 focus:ring-primary/40"
            onKeyDown={(e) => {
              if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                void handleSendReply()
              }
            }}
          />
          <Button
            size="sm"
            className="h-8 w-8 p-0 shrink-0"
            disabled={!replyText.trim() || isSending}
            onClick={() => void handleSendReply()}
          >
            {isSending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          </Button>
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────

type FilterMode = 'all' | 'open' | 'resolved'

interface CommentsPanelProps {
  projectId: string
  sceneId: string
  paragraphId: string
}

export default function CommentsPanel({ projectId, sceneId, paragraphId }: CommentsPanelProps) {
  const {
    paragraphComments,
    isCommentsLoading,
    fetchParagraphComments,
    addParagraphComment,
    replyParagraphComment,
    resolveParagraphComment,
  } = useProjectStore()

  const comments: ParagraphComment[] = paragraphComments[paragraphId] || []
  const [filter, setFilter] = useState<FilterMode>('open')
  const [newComment, setNewComment] = useState('')
  const [isAdding, setIsAdding] = useState(false)

  useEffect(() => {
    void fetchParagraphComments(projectId, sceneId, paragraphId)
  }, [paragraphId, projectId, sceneId, fetchParagraphComments])

  const filtered = comments.filter((c) => {
    // Older records used `pending` for active threads. Treat every
    // non-resolved status as open so those comments do not disappear.
    if (filter === 'open') return c.status !== 'resolved'
    if (filter === 'resolved') return c.status === 'resolved'
    return true
  })

  const openCount = comments.filter((c) => c.status !== 'resolved').length
  const resolvedCount = comments.filter((c) => c.status === 'resolved').length

  const handleAddComment = async () => {
    if (!newComment.trim()) return
    setIsAdding(true)
    try {
      await addParagraphComment(projectId, sceneId, paragraphId, newComment.trim())
      setNewComment('')
    } finally {
      setIsAdding(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/10 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <MessageSquare className="h-3.5 w-3.5" />
          Comments
        </span>
        <Button
          size="sm"
          variant="ghost"
          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
          onClick={() => fetchParagraphComments(projectId, sceneId, paragraphId)}
          title="Refresh comments"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-0.5 px-3 py-1.5 border-b bg-muted/5 shrink-0">
        {(['open', 'resolved', 'all'] as FilterMode[]).map((mode) => {
          const count = mode === 'open' ? openCount : mode === 'resolved' ? resolvedCount : comments.length
          return (
            <button
              key={mode}
              onClick={() => setFilter(mode)}
              className={`text-[10px] font-semibold px-2 py-0.5 rounded transition-colors capitalize ${
                filter === mode
                  ? 'bg-background border text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {mode} {count > 0 && <span className="opacity-60">({count})</span>}
            </button>
          )
        })}
      </div>

      {/* Comment list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {isCommentsLoading && comments.length === 0 && (
          <div className="flex items-center justify-center py-12 gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-xs">Loading comments…</span>
          </div>
        )}

        {!isCommentsLoading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-muted-foreground text-center">
            <MessageCircle className="h-7 w-7 text-muted-foreground/30" />
            <p className="text-xs">
              {filter === 'open' ? 'No open comments.' : filter === 'resolved' ? 'No resolved comments.' : 'No comments yet.'}
            </p>
          </div>
        )}

        {filtered.map((comment) => (
          <CommentThread
            key={comment.comment_id}
            comment={comment}
            projectId={projectId}
            sceneId={sceneId}
            onResolve={() => void resolveParagraphComment(projectId, sceneId, paragraphId, comment.comment_id)}
            onReply={(content) => replyParagraphComment(projectId, sceneId, paragraphId, comment.comment_id, content)}
          />
        ))}
      </div>

      {/* Add comment */}
      <div className="border-t p-3 shrink-0 bg-muted/5">
        <div className="flex items-end gap-2">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment… (Ctrl+Enter to send)"
            rows={3}
            className="flex-1 text-[12px] resize-none border rounded-lg px-3 py-2 bg-background focus:outline-none focus:ring-1 focus:ring-primary/40 leading-relaxed"
            onKeyDown={(e) => {
              if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                void handleAddComment()
              }
            }}
          />
          <Button
            size="sm"
            className="h-9 w-9 p-0 shrink-0"
            disabled={!newComment.trim() || isAdding}
            onClick={() => void handleAddComment()}
            title="Add comment (Ctrl+Enter)"
          >
            {isAdding ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1.5">Ctrl+Enter to send</p>
      </div>
    </div>
  )
}
