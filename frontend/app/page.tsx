import Link from "next/link"
import { ArrowRight, CheckCircle2, FileText, Lightbulb, PenLine, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import AppHeader from "@/components/AppHeader"
import FirstRunStatus from "@/components/FirstRunStatus"

const steps = [
  { icon: Lightbulb, title: "Plan", text: "Start from a few sentences. The AI suggests characters, a world and plot threads; you keep what you like." },
  { icon: PenLine, title: "Write", text: "Describe what happens next and get a draft chapter. Edit every word; nothing is final until you approve it." },
  { icon: CheckCircle2, title: "Review", text: "The AI picks out new facts from each chapter. Confirm them, and later chapters stay consistent." },
  { icon: FileText, title: "Finish", text: "Put approved chapters together and export DOCX, EPUB, PDF, HTML, Markdown or plain text." },
]

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-8">
        <section className="mx-auto max-w-3xl text-center">
          <p className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
            <Sparkles className="h-4 w-4" />Runs on your computer
          </p>
          <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">Write your novel, one clear step at a time</h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg leading-8 text-muted-foreground">
            Plan the story, write chapters with an AI partner and keep hundreds of story facts straight. You stay in charge of every word.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" className="gap-2">
              <Link href="/projects">Open your novels<ArrowRight className="h-4 w-4" /></Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/settings">Set up AI</Link>
            </Button>
          </div>
        </section>

        <FirstRunStatus />

        <section className="mt-16" aria-labelledby="how-it-works">
          <h2 id="how-it-works" className="text-center text-sm font-medium text-muted-foreground">How it works</h2>
          <ol className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map(({ icon: Icon, title, text }, index) => (
              <li key={title} className="rounded-xl border bg-card p-5 shadow-soft">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon className="h-5 w-5" /></span>
                  <span className="text-xs font-medium text-muted-foreground">Step {index + 1}</span>
                </div>
                <h3 className="mt-4 font-semibold">{title}</h3>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">{text}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>
    </div>
  )
}
