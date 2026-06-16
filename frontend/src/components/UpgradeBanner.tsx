import { Link } from 'react-router-dom'
import { Lock, Sparkles } from 'lucide-react'

interface Props {
  title: string
  desc: string
}

export function UpgradeBanner({ title, desc }: Props) {
  return (
    <div className="card p-8 border-2 border-dashed border-gold-300
      bg-gold-50/40 text-center">
      <div className="inline-flex items-center justify-center w-12 h-12
        rounded-xl bg-gold-100 mb-3">
        <Lock className="h-6 w-6 text-gold-600" />
      </div>
      <h3 className="font-bold text-obsidian-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-600 max-w-md mx-auto mb-5">{desc}</p>
      <Link to="/account"
        className="btn-primary inline-flex items-center gap-2">
        <Sparkles className="h-4 w-4" />
        Mejorar mi plan
      </Link>
    </div>
  )
}
