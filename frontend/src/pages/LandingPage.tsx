import { Link } from "react-router-dom"
import {
  ArrowRight,
  BookOpen,
  Gavel,
  Shield,
  Zap,
  Database,
  Brain,
  Search,
  ExternalLink,
  Code2,
} from "lucide-react"
import { Logo } from "@/components/brand/Logo"
import { Button } from "@/components/ui/button"

const features = [
  {
    icon: BookOpen,
    title: "USCIS Policy Manual",
    desc: "657+ policy sections scraped live and indexed for semantic search across visa categories.",
  },
  {
    icon: Gavel,
    title: "BIA & Court Precedents",
    desc: "5,800+ Board of Immigration Appeals decisions plus live CourtListener federal case search.",
  },
  {
    icon: Brain,
    title: "GPT-4o with Citations",
    desc: "Structured legal research answers with cited laws, case precedents, and important disclaimers.",
  },
  {
    icon: Shield,
    title: "PII Guardrails",
    desc: "GLiNER entity redaction and LlamaGuard safety checks before every response is returned.",
  },
  {
    icon: Search,
    title: "Hybrid Retrieval",
    desc: "Dense vector search + BM25 keyword matching, fused and reranked with Cohere for precision.",
  },
  {
    icon: Database,
    title: "Full Audit Trail",
    desc: "Every query logged with response time, token count, and user feedback for firm compliance.",
  },
]

const stack = ["FastAPI", "React 19", "Milvus", "PostgreSQL", "Redis", "Celery", "Docker", "LangSmith"]

const metrics = [
  { value: "0.840", label: "RAGAS Score" },
  { value: "287+", label: "Documents Indexed" },
  { value: "<30s", label: "Avg Response" },
  { value: "100%", label: "Cited Answers" },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <nav className="sticky top-0 z-50 border-b border-slate-100 bg-white/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Logo size="sm" showTagline={false} />
          <div className="flex items-center gap-3">
            <a
              href="https://github.com/Nithishkaranam2002/ImmigraAssist"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"
            >
              <Code2 className="w-4 h-4" />
              Source Code
            </a>
            <Link to="/login">
              <Button variant="ghost" size="sm">Sign In</Button>
            </Link>
            <Link to="/login">
              <Button size="sm">
                Try Live Demo <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <section className="gradient-hero text-white relative overflow-hidden">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-10 left-1/4 w-96 h-96 rounded-full bg-brand-400 blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-80 h-80 rounded-full bg-violet-500 blur-3xl" />
        </div>
        <div className="relative max-w-6xl mx-auto px-6 py-20 sm:py-28">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 text-xs font-medium mb-6">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Live at 157.230.51.229
          </div>
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-semibold leading-[1.1] max-w-3xl">
            Immigration legal research, from policies to precedents.
          </h1>
          <p className="mt-6 text-lg text-slate-300 max-w-2xl leading-relaxed">
            Production-grade RAG system for immigration law firms. Ask about H1B, asylum,
            green cards — get cited answers backed by USCIS policies and case law in seconds.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/login">
              <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 h-12 px-6">
                <Zap className="w-4 h-4 mr-2" />
                Launch Demo
              </Button>
            </Link>
            <a href="https://github.com/Nithishkaranam2002/ImmigraAssist" target="_blank" rel="noopener noreferrer">
              <Button
                size="lg"
                variant="outline"
                className="h-12 px-6 border-white/40 bg-transparent text-white hover:bg-white/15 hover:text-white shadow-none"
              >
                View Source <ExternalLink className="w-4 h-4 ml-2" />
              </Button>
            </a>
          </div>
          <div className="mt-14 grid grid-cols-2 sm:grid-cols-4 gap-6">
            {metrics.map((m) => (
              <div key={m.label}>
                <p className="text-2xl sm:text-3xl font-bold">{m.value}</p>
                <p className="text-xs text-slate-400 mt-1">{m.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">Built for real legal workflows</h2>
          <p className="text-slate-500 mt-2 max-w-xl mx-auto">
            Not a chatbot wrapper — a full retrieval pipeline with hybrid search, reranking, and compliance guardrails.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => (
            <div
              key={f.title}
              className="p-6 rounded-2xl border border-slate-200 bg-white hover:border-brand-200 hover:shadow-md transition-all group"
            >
              <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center mb-4 group-hover:bg-brand-100 transition-colors">
                <f.icon className="w-5 h-5 text-brand-600" />
              </div>
              <h3 className="font-semibold text-slate-900 mb-2">{f.title}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-slate-50 border-y border-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-xl font-bold text-slate-900 mb-6 text-center">Tech Stack</h2>
          <div className="flex flex-wrap justify-center gap-3">
            {stack.map((t) => (
              <span
                key={t}
                className="px-4 py-2 rounded-full bg-white border border-slate-200 text-sm font-medium text-slate-700 shadow-sm"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-20 text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">Ready to explore?</h2>
        <p className="text-slate-500 mt-2 mb-8">
          Sign in with the demo account and ask any immigration law question.
        </p>
        <Link to="/login">
          <Button size="lg" className="h-12 px-8">
            Get Started <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </Link>
      </section>

      <footer className="border-t border-slate-200 bg-slate-50">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <p>© 2026 ImmigraAssist · Built by Nithish Karanam</p>
          <p className="text-center max-w-md">
            Not legal advice. AI-generated research summaries require attorney review before client use.
          </p>
        </div>
      </footer>
    </div>
  )
}
