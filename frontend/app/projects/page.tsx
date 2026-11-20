"use client"

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertTriangle, Archive, BookOpen, ChevronLeft, ChevronRight, Copy, MoreHorizontal, Plus, RotateCcw, Search, Star, Trash2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { useProjectStore } from '@/store/projectStore'
import AppHeader from '@/components/AppHeader'
import { EmptyState, LoadingState, ProgressBar } from '@/components/ui/page'
import { rc6Api } from '@/lib/api'
import type { ProjectLibraryItem, ProjectLibraryPage } from '@/types'

type ProjectView = 'active' | 'archived' | 'trash'
type PendingAction = { type: 'trash' | 'purge' | 'duplicate'; project: ProjectLibraryItem } | null

export default function ProjectsPage() {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [view, setView] = useState<ProjectView>('active')
  const [page, setPage] = useState(1)
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [library, setLibrary] = useState<ProjectLibraryPage | null>(null)
  const [libraryLoading, setLibraryLoading] = useState(true)
  const [libraryRevision, setLibraryRevision] = useState(0)
  const [openMenu, setOpenMenu] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<PendingAction>(null)
  const [confirmationTitle, setConfirmationTitle] = useState('')
  const [newStoryTitle, setNewStoryTitle] = useState('')
  const {
    loading,
    error,
    newProjectTitle,
    newProjectIdeaDump,
    newProjectGenre,
    newProjectTone,
    createProject,
    deleteProject,
    archiveProject,
    unarchiveProject,
    restoreProject,
    purgeProject,
    duplicateProject,
    setNewProjectTitle,
    setNewProjectIdeaDump,
    setNewProjectGenre,
    setNewProjectTone,
  } = useProjectStore()

  const loadLibrary = useCallback(async () => {
    setLibraryLoading(true)
    try {
      setLibrary(await rc6Api.getProjectLibrary({
        status: view === 'trash' ? 'trashed' : view,
        search: query.trim(),
        page,
        page_size: 24,
        favorites_only: view === 'active' && favoritesOnly,
      }))
    } finally {
      setLibraryLoading(false)
    }
  }, [favoritesOnly, page, query, view])

  useEffect(() => {
    const timer = window.setTimeout(() => void loadLibrary(), 250)
    return () => window.clearTimeout(timer)
  }, [libraryRevision, loadLibrary])

  useEffect(() => {
    setPage(1)
  }, [query, view, favoritesOnly])

  const counts = library?.counts || { active: 0, archived: 0, trashed: 0, favorites: 0 }
  const displayedProjects = library?.items || []

  const closeAction = () => {
    setPendingAction(null)
    setConfirmationTitle('')
  }

  const handleCreate = async () => {
    if (!newProjectTitle.trim() || !newProjectIdeaDump.trim()) return
    const project = await createProject({
      title: newProjectTitle.trim(),
      project_name: newProjectTitle.trim(),
      story_title: newStoryTitle.trim() || null,
      premise: '',
      idea_dump: newProjectIdeaDump.trim(),
      genre: newProjectGenre.trim(),
      tone: newProjectTone.trim(),
      themes: [],
      inspirations: [],
      target_length: 'unknown',
      audience: 'emerging',
      narrative_goals: ['Develop the story before chapter drafting.'],
    })
    if (project) router.push(`/project/${project.id}`)
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-background">
      <AppHeader />
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-8">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-semibold tracking-tight">Your novels</h1>
            <p className="mt-1 max-w-2xl text-[15px] text-muted-foreground">Pick up where you left off, or start a new book from an idea.</p>
          </div>
          <Button type="button" onClick={() => setShowCreate((value) => !value)} data-testid="create-project-toggle">
            <Plus className="mr-2 h-4 w-4" />
            New novel
          </Button>
        </header>

        {error && <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

        <section className="flex flex-col gap-3 md:flex-row md:items-center">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search projects"
              className="pl-9"
              data-testid="project-search"
            />
          </div>
          {view === 'active' ? (
            <Button type="button" variant={favoritesOnly ? 'default' : 'outline'} onClick={() => setFavoritesOnly((value) => !value)} aria-pressed={favoritesOnly}>
              <Star className={`mr-2 h-4 w-4 ${favoritesOnly ? 'fill-current' : ''}`} />
              Favorites ({counts.favorites})
            </Button>
          ) : null}
        </section>

        <nav className="inline-flex w-fit flex-wrap gap-1 rounded-lg bg-muted p-1" aria-label="Project lists">
          {(['active', 'archived', 'trash'] as ProjectView[]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setView(item)}
              aria-current={view === item ? 'page' : undefined}
              data-testid={`projects-view-${item}`}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${view === item ? 'bg-background font-medium text-foreground shadow-soft' : 'text-muted-foreground hover:text-foreground'}`}
            >
              {item === 'active' ? 'Active' : item === 'archived' ? 'Archived' : 'Trash'} ({item === 'trash' ? counts.trashed : counts[item]})
            </button>
          ))}
        </nav>

        {showCreate && (
          <section className="grid gap-4 rounded-xl border bg-card p-6 shadow-soft md:grid-cols-2" data-testid="create-project-panel">
            <div className="md:col-span-2">
              <h2 className="text-lg font-semibold">Start a new novel</h2>
              <p className="mt-1 text-sm text-muted-foreground">Only the name and a rough idea are needed. You can change everything later.</p>
            </div>
            <div className="min-w-0 space-y-2 md:col-span-2">
              <Label htmlFor="idea_dump">Your story idea</Label>
              <Textarea id="idea_dump" value={newProjectIdeaDump} onChange={(event) => setNewProjectIdeaDump(event.target.value)} rows={4} placeholder="A few sentences: who is the story about, what do they want, what stands in the way?" />
            </div>
            <div className="min-w-0 space-y-2">
              <Label htmlFor="project-name">Project name</Label>
              <Input id="project-name" placeholder="e.g. Memory Fantasy Experiment" value={newProjectTitle} onChange={(event) => setNewProjectTitle(event.target.value)} />
              <p className="text-xs text-muted-foreground">How you find it in this list.</p>
            </div>
            <div className="min-w-0 space-y-2">
              <Label htmlFor="story-title">Story title <span className="font-normal text-muted-foreground">(optional)</span></Label>
              <Input id="story-title" placeholder="Untitled for now" value={newStoryTitle} onChange={(event) => setNewStoryTitle(event.target.value)} />
              <p className="text-xs text-muted-foreground">The title readers see in the exported book.</p>
            </div>
            <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="min-w-0 space-y-2">
                <Label htmlFor="genre">Genre</Label>
                <Input id="genre" value={newProjectGenre} onChange={(event) => setNewProjectGenre(event.target.value)} />
              </div>
              <div className="min-w-0 space-y-2">
                <Label htmlFor="tone">Tone</Label>
                <Input id="tone" value={newProjectTone} onChange={(event) => setNewProjectTone(event.target.value)} />
              </div>
            </div>
            <div className="flex flex-wrap gap-2 md:col-span-2">
              <Button onClick={handleCreate} disabled={loading} data-testid="create-project">
                <Plus className="mr-2 h-4 w-4" />
                Create novel
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </section>
        )}

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="projects-grid">
          {libraryLoading ? (
            <LoadingState className="sm:col-span-2 xl:col-span-3">Loading your novels…</LoadingState>
          ) : displayedProjects.length === 0 ? (
            <EmptyState
              className="sm:col-span-2 xl:col-span-3"
              icon={<BookOpen className="h-5 w-5" />}
              title={query.trim() ? 'No novels match your search' : view === 'active' ? 'No novels yet' : view === 'archived' ? 'Nothing archived' : 'Trash is empty'}
              description={query.trim() ? 'Try a different word, or clear the search.' : view === 'active' ? 'Start with an idea. The AI helps you plan, write and finish the book.' : undefined}
              action={view === 'active' && !query.trim() ? <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" />New novel</Button> : undefined}
            />
          ) : displayedProjects.map((project) => (
            <article key={project.id} className="relative flex min-w-0 flex-col rounded-xl border bg-card p-5 shadow-soft transition-shadow hover:shadow-md">
              <button
                type="button"
                onClick={() => router.push(`/project/${project.id}`)}
                className="block w-full min-w-0 text-left"
                data-testid="project-card"
              >
                <div className="min-w-0 pr-16">
                  <h2 className="truncate text-lg font-semibold">{project.project_name || project.title}</h2>
                  {project.story_title && project.story_title !== (project.project_name || project.title) ? <p className="truncate text-sm text-muted-foreground">“{project.story_title}”</p> : null}
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded-full bg-primary/10 px-2.5 py-0.5 font-medium text-primary">{project.milestone}</span>
                  {project.genre ? <span className="text-muted-foreground">{project.genre}</span> : null}
                </div>
                {project.completeness != null ? (
                  <div className="mt-4">
                    <div className="mb-1 flex justify-between text-xs text-muted-foreground"><span>Story plan</span><span>{Math.round(project.completeness)}%</span></div>
                    <ProgressBar value={project.completeness} label="Story plan completeness" />
                  </div>
                ) : null}
                <p className="mt-4 truncate text-xs text-muted-foreground">{project.last_opened_at ? `Opened ${new Date(project.last_opened_at).toLocaleDateString()}` : `Updated ${new Date(project.updated_at || project.created_at).toLocaleDateString()}`}</p>
              </button>
              {view !== 'trash' ? <button type="button" className="absolute right-12 top-3 rounded-full p-2 text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label={`${project.favorite ? 'Remove' : 'Add'} ${project.project_name || project.title} ${project.favorite ? 'from' : 'to'} favorites`} onClick={async () => { await rc6Api.setFavorite(project.id, !project.favorite); setLibraryRevision((value) => value + 1) }}><Star className={`h-4 w-4 ${project.favorite ? 'fill-amber-400 text-amber-500' : ''}`} /></button> : null}
              <button type="button" className="absolute right-3 top-3 rounded-full p-2 text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label={`More actions for ${project.project_name || project.title}`} aria-expanded={openMenu === project.id} onClick={() => setOpenMenu((value) => value === project.id ? null : project.id)}><MoreHorizontal className="h-4 w-4" /></button>
              {openMenu === project.id ? (
                <div className="absolute right-3 top-12 z-10 w-48 rounded-lg border bg-card p-1 shadow-xl" role="menu">
                  {view === 'active' ? <><button className="flex w-full items-center rounded-md px-3 py-2 text-left text-sm hover:bg-muted" onClick={() => { setPendingAction({ type: 'duplicate', project }); setOpenMenu(null) }} data-testid="duplicate-project"><Copy className="mr-2 h-4 w-4" />Duplicate</button><button className="flex w-full items-center rounded-md px-3 py-2 text-left text-sm hover:bg-muted" onClick={async () => { setOpenMenu(null); await archiveProject(project.id); setLibraryRevision((value) => value + 1) }} data-testid="archive-project"><Archive className="mr-2 h-4 w-4" />Archive</button><button className="flex w-full items-center rounded-md px-3 py-2 text-left text-sm text-destructive hover:bg-destructive/10" onClick={() => { setPendingAction({ type: 'trash', project }); setOpenMenu(null) }} data-testid="delete-project"><Trash2 className="mr-2 h-4 w-4" />Move to Trash</button></> : null}
                  {view === 'archived' ? <button className="flex w-full items-center rounded-md px-3 py-2 text-left text-sm hover:bg-muted" onClick={async () => { setOpenMenu(null); await unarchiveProject(project.id); setLibraryRevision((value) => value + 1) }} data-testid="unarchive-project"><RotateCcw className="mr-2 h-4 w-4" />Return to Active</button> : null}
                  {view === 'trash' ? <><button className="flex w-full items-center rounded-md px-3 py-2 text-left text-sm hover:bg-muted" onClick={async () => { setOpenMenu(null); await restoreProject(project.id); setLibraryRevision((value) => value + 1) }} data-testid="restore-project"><RotateCcw className="mr-2 h-4 w-4" />Restore</button><button className="flex w-full items-center rounded-md px-3 py-2 text-left text-sm text-destructive hover:bg-destructive/10" onClick={() => { setPendingAction({ type: 'purge', project }); setOpenMenu(null) }} data-testid="purge-project"><Trash2 className="mr-2 h-4 w-4" />Delete Permanently</button></> : null}
                </div>
              ) : null}
            </article>
          ))}
        </section>
        {library && library.pages > 1 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
            <span>Page {library.page} of {library.pages} · {library.total} projects</span>
            <div className="flex gap-2"><Button type="button" size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((value) => value - 1)} aria-label="Previous project page"><ChevronLeft className="h-4 w-4" /></Button><Button type="button" size="sm" variant="outline" disabled={!library.has_next} onClick={() => setPage((value) => value + 1)} aria-label="Next project page"><ChevronRight className="h-4 w-4" /></Button></div>
          </div>
        ) : null}
      </div>

      {pendingAction ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation" onMouseDown={(event) => {
          if (event.currentTarget === event.target) closeAction()
        }}>
          <section className="w-full max-w-lg rounded-xl border bg-card p-5 shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="project-action-title">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <span className="rounded-full bg-amber-100 p-2 text-amber-700"><AlertTriangle className="h-5 w-5" /></span>
                <div>
                  <h2 id="project-action-title" className="text-lg font-semibold">
                    {pendingAction.type === 'duplicate' ? 'Duplicate project' : pendingAction.type === 'purge' ? 'Delete permanently?' : 'Move project to Trash?'}
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {pendingAction.type === 'duplicate'
                      ? 'Copy just the setup (idea, genre, settings), or the whole story including chapters and confirmed facts. AI history is not copied.'
                      : pendingAction.type === 'purge'
                        ? 'This erases the project and all owned story data. It cannot be undone.'
                        : 'The project and its story data will be preserved and can be restored from Trash.'}
                  </p>
                </div>
              </div>
              <button type="button" onClick={closeAction} aria-label="Close confirmation" className="rounded-md p-1 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><X className="h-4 w-4" /></button>
            </div>

            {pendingAction.type === 'purge' ? (
              <div className="mt-5 space-y-2">
                <Label htmlFor="confirmation-title">Type <strong>{pendingAction.project.project_name || pendingAction.project.title}</strong> to confirm</Label>
                <Input id="confirmation-title" autoFocus value={confirmationTitle} onChange={(event) => setConfirmationTitle(event.target.value)} data-testid="purge-confirmation-title" />
              </div>
            ) : null}

            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <Button variant="outline" onClick={closeAction}>Cancel</Button>
              {pendingAction.type === 'duplicate' ? (
                <>
                  <Button variant="outline" onClick={async () => {
                    const copy = await duplicateProject(pendingAction.project.id, 'shell')
                    closeAction()
                    if (copy) router.push(`/project/${copy.id}`)
                  }}>Copy Setup Only</Button>
                  <Button onClick={async () => {
                    const copy = await duplicateProject(pendingAction.project.id, 'story')
                    closeAction()
                    if (copy) router.push(`/project/${copy.id}`)
                  }} data-testid="duplicate-story-content">Copy Story Content</Button>
                </>
              ) : pendingAction.type === 'purge' ? (
                <Button
                  variant="destructive"
                  disabled={confirmationTitle.trim() !== (pendingAction.project.project_name || pendingAction.project.title).trim() || loading}
                  onClick={async () => {
                    await purgeProject(pendingAction.project.id, confirmationTitle)
                    closeAction()
                    setLibraryRevision((value) => value + 1)
                  }}
                  data-testid="confirm-purge-project"
                >
                  Delete Permanently
                </Button>
              ) : (
                <Button variant="destructive" onClick={async () => {
                  await deleteProject(pendingAction.project.id)
                  closeAction()
                  setLibraryRevision((value) => value + 1)
                }} data-testid="confirm-trash-project">Move to Trash</Button>
              )}
            </div>
          </section>
        </div>
      ) : null}
    </main>
  )
}
