import Link from "next/link"
import { Button } from "@/components/ui/button"
import FirstRunStatus from "@/components/FirstRunStatus"

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-white mb-4">NovelForge</h1>
          <p className="text-2xl text-purple-200 mb-3">Narrative Intelligence for long-form fiction</p>
          <p className="mx-auto mb-8 max-w-3xl text-slate-300">Understand the whole novel, govern canon, trace chronology, develop characters, and move from concept to publication with evidence-backed guidance.</p>
          <div className="flex gap-4 justify-center">
            <Link href="/projects">
              <Button size="lg" className="text-lg">
                Open Projects
              </Button>
            </Link>
            <Link href="/settings">
              <Button size="lg" variant="outline" className="text-lg">
                AI Settings
              </Button>
            </Link>
          </div>
          <FirstRunStatus />
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6">
            <h3 className="text-xl font-semibold text-white mb-2">Understand</h3>
            <p className="text-purple-200">
              See Story Health, narrative completeness, unresolved threads, pacing, and continuity in one connected platform.
            </p>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6">
            <h3 className="text-xl font-semibold text-white mb-2">Govern</h3>
            <p className="text-purple-200">
              Keep official canon, chronology, character knowledge, and the Story Bible transparent and author-controlled.
            </p>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6">
            <h3 className="text-xl font-semibold text-white mb-2">Progress</h3>
            <p className="text-purple-200">
              Follow clear milestones from Concept Complete through Publication Ready, with direct next actions at every stage.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
