"use client"

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertTriangle, Archive, ChevronLeft, ChevronRight, Copy, FolderOpen, MoreHorizontal, Plus, RotateCcw, Search, Star, Trash2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { useProjectStore } from '@/store/projectStore'
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
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">Narrative Studio</p>
            <h1 className="truncate text-3xl font-semibold">Projects</h1>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Create a novel workspace or return to one in progress. Each project keeps its story intelligence, canon, milestones, and writing history together.</p>
          </div>
          <Button type="button" onClick={() => setShowCreate((value) => !value)} data-testid="create-project-toggle">
            <Plus className="mr-2 h-4 w-4" />
            Create Project
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
          <div className="text-sm text-muted-foreground">Newest first</div>
          {view === 'active' ? (
            <Button type="button" variant={favoritesOnly ? 'default' : 'outline'} onClick={() => setFavoritesOnly((value) => !value)} aria-pressed={favoritesOnly}>
              <Star className={`mr-2 h-4 w-4 ${favoritesOnly ? 'fill-current' : ''}`} />
              Favorites ({counts.favorites})
            </Button>
          ) : null}
        </section>

        <nav className="flex flex-wrap gap-2 border-b pb-3" aria-label="Project lifecycle views">
          {(['active', 'archived', 'trash'] as ProjectView[]).map((item) => (
            <Button
              key={item}
              type="button"
              size="sm"
              variant={view === item ? 'default' : 'outline'}
              onClick={() => setView(item)}
              aria-current={view === item ? 'page' : undefined}
              data-testid={`projects-view-${item}`}
            >
              {item === 'active' ? 'Active' : item === 'archived' ? 'Archived' : 'Trash'} ({item === 'trash' ? counts.trashed : counts[item]})
            </Button>
          ))}
        </nav>

        {showCreate && (
          <section className="grid gap-4 rounded-md border bg-card p-4 md:grid-cols-2" data-testid="create-project-panel">
            <div className="min-w-0 space-y-2">
              <Label htmlFor="project-name">Project name</Label>
              <Input id="project-name" placeholder="e.g. Memory Fantasy Experiment" value={newProjectTitle} onChange={(event) => setNewProjectTitle(event.target.value)} />
              <p className="text-xs text-muted-foreground">Your private workspace name. It can be different from the novel title.</p>
            </div>
            <div className="min-w-0 space-y-2">
              <Label htmlFor="story-title">Story title <span className="font-normal text-muted-foreground">(optional)</span></Label>
              <Input id="story-title" placeholder="Untitled for now" value={newStoryTitle} onChange={(event) => setNewStoryTitle(event.target.value)} />
              <p className="text-xs text-muted-foreground">Reader-facing title used for the manuscript and exports.</p>
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
            <div className="min-w-0 space-y-2 md:col-span-2">
              <Label htmlFor="idea_dump">Story seed</Label>
              <Textarea id="idea_dump" value={newProjectIdeaDump} onChange={(event) => setNewProjectIdeaDump(event.target.value)} rows={5} />
            </div>
            <div className="md:col-span-2">
              <Button onClick={handleCreate} disabled={loading} data-testid="create-project">
                <Plus className="mr-2 h-4 w-4" />
                Create
              </Button>
            </div>
          </section>
        )}

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" data-testid="projects-grid">
          {libraryLoading ? (
            <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">Loading your project library…</div>
          ) : displayedProjects.length === 0 ? (
            <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">No projects match this view. Clear the search, show all projects, or create a project to start your novel.</div>
          ) : displayedProjects.map((project) => (
            <article key={project.id} className="relative min-w-0 rounded-md border bg-card p-4">
              <button
                type="button"
                onClick={() => router.push(`/project/${project.id}`)}
                className="block w-full min-w-0 text-left"
                data-testid="project-card"
              >
                <div className="flex min-w-0 items-center gap-2 pr-16">
                  <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <h2 className="truncate text-lg font-semibold">{project.project_name || project.title}</h2>
                </div>
                <p className="mt-1 truncate text-sm">Novel: <span className="font-medium">{project.story_title || 'Untitled'}</span></p>
                <p className="mt-2 truncate text-sm text-muted-foreground">{project.last_opened_at ? `Last opened ${new Date(project.last_opened_at).toLocaleString()}` : `Updated ${new Date(project.updated_at || project.created_at).toLocaleString()}`}</p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full bg-violet-50 px-2 py-1 font-semibold text-violet-800">{project.milestone}</span>
                  {project.story_consistency != null ? <span className="rounded-full bg-sky-50 px-2 py-1 text-sky-800">Consistency {project.story_consistency}</span> : null}
                  {project.completeness != null ? <span className="rounded-full bg-emerald-50 px-2 py-1 text-emerald-800">Complete {Math.round(project.completeness)}%</span> : null}
                </div>
              </button>
              {view !== 'trash' ? <button type="button" className="absolute right-12 top-3 rounded-full p-2 text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label={`${project.favorite ? 'Remove' : 'Add'} ${project.project_name || project.title} ${project.favorite ? 'from' : 'to'} favorites`} onClick={async () => { await rc6Api.setFavorite(project.id, !project.favorite); setLibraryRevision((value) => value + 1) }}><Star className={`h-4 w-4 ${project.favorite ? 'fill-amber-400 text-amber-500' : ''}`} /></button> : null}
              <button type="button" className="absolute right-3 top-3 rounded-full p-2 text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label={`More actions for ${project.project_name || project.title}`} aria-expanded={openMenu === project.id} onClick={() => setOpenMenu((value) => value === project.id ? null : project.id)}><MoreHorizontal className="h-4 w-4" /></button>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => router.push(`/project/${project.id}`)}>
                  <FolderOpen className="mr-2 h-4 w-4" />
                  Open
                </Button>
              </div>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4" role="presentation" onMouseDown={(event) => {
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
                      ? 'Choose whether to copy setup only or include governed story content. Analysis caches and AI run history are never copied.'
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
