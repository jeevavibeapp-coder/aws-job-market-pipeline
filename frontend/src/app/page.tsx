import Link from 'next/link'
import { Search, Zap, Target, Shield, TrendingUp, Clock } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white">
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <Target className="w-5 h-5" />
          </div>
          <span className="text-xl font-bold">JobIntel</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-slate-300 hover:text-white transition-colors">
            Sign in
          </Link>
          <Link
            href="/register"
            className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Get started
          </Link>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-8 py-24">
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-2 text-sm text-blue-300 mb-8">
            <Zap className="w-4 h-4" />
            AI-powered job matching
          </div>
          <h1 className="text-6xl font-bold mb-6 leading-tight">
            Find jobs that{' '}
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              actually fit you
            </span>
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10">
            Stop scrolling through hundreds of irrelevant listings. Our AI filters jobs by your
            exact skills, experience, and preferences — then ranks them so the best opportunities
            rise to the top.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/register"
              className="bg-blue-600 hover:bg-blue-500 px-8 py-3 rounded-xl font-semibold text-lg transition-colors"
            >
              Start for free
            </Link>
            <Link
              href="/login"
              className="border border-white/20 hover:border-white/40 px-8 py-3 rounded-xl font-semibold text-lg transition-colors"
            >
              Sign in
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24">
          {[
            {
              icon: <Target className="w-6 h-6 text-blue-400" />,
              title: 'AI Scoring',
              desc: 'Every job gets a match score across skills, experience, location, and seniority. Only 70+ scores shown.',
            },
            {
              icon: <Shield className="w-6 h-6 text-green-400" />,
              title: 'Direct Apply Links',
              desc: 'We always surface the company career page URL. Never waste time with LinkedIn Easy Apply when a direct link exists.',
            },
            {
              icon: <Clock className="w-6 h-6 text-purple-400" />,
              title: 'Freshness First',
              desc: 'Default view shows jobs posted in the last 24 hours. Low competition jobs posted today with few applicants rise to the top.',
            },
            {
              icon: <Search className="w-6 h-6 text-yellow-400" />,
              title: 'Natural Language Search',
              desc: '"Find Data Engineer jobs in Chennai posted this week requiring Python and Snowflake" — just type it.',
            },
            {
              icon: <TrendingUp className="w-6 h-6 text-cyan-400" />,
              title: 'Application Tracker',
              desc: 'CRM-style pipeline to track every application from Saved → Applied → Interview → Offer.',
            },
            {
              icon: <Zap className="w-6 h-6 text-orange-400" />,
              title: 'Smart Experience Match',
              desc: 'Requires 5 years but you have 2.5? Auto-rejected. Requires 2 years? Accepted. Intelligent, not just keyword matching.',
            },
          ].map((f) => (
            <div key={f.title} className="bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/8 transition-colors">
              <div className="mb-4">{f.icon}</div>
              <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
