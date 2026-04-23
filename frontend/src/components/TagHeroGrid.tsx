import { useSearchParams } from 'react-router-dom'
import { TAG_CONFIG } from '../data/subtags'

const TAG_ORDER = ['CD', 'ME', 'E', 'PET'] as const

const TAG_ICONS: Record<string, string> = {
  CD: '🏠',
  ME: '✨',
  E: '⚡',
  PET: '🐾',
}

export default function TagHeroGrid() {
  const [, setSearchParams] = useSearchParams()

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {TAG_ORDER.map(tagKey => {
        const config = TAG_CONFIG[tagKey]
        const icon = TAG_ICONS[tagKey]
        return (
          <button
            key={tagKey}
            onClick={() => setSearchParams({ tag: tagKey })}
            className="group relative flex flex-col gap-3 p-5 bg-black-deep border border-gray-steel cursor-pointer transition-all duration-200 text-left hover:bg-neon-green hover:border-neon-green hover:shadow-[0_0_20px_rgba(0,255,65,0.3)] hover:-translate-y-1"
          >
            <span className="absolute top-4 right-4 font-mono text-gray-text group-hover:text-black transition-colors text-lg">
              →
            </span>
            <span className="text-3xl mb-1">{icon}</span>
            <span className="font-mono text-sm font-bold tracking-[0.2em] uppercase text-gray-light group-hover:text-black transition-colors">
              {config.label}
            </span>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {config.subtags.map(sub => (
                <button
                  key={sub.value}
                  type="button"
                  onClick={e => {
                    e.stopPropagation()
                    setSearchParams({ tag: tagKey, subtag: sub.value })
                  }}
                  className="font-mono text-[11px] font-bold tracking-wider uppercase px-3 py-1 border border-neon-green/40 text-neon-green bg-black/30 hover:bg-neon-green hover:text-black hover:border-neon-green hover:shadow-[0_0_8px_rgba(0,255,65,0.4)] group-hover:border-black/50 group-hover:text-black group-hover:bg-black/20 group-hover:hover:bg-black/40 group-hover:hover:text-black transition-all duration-150 cursor-pointer"
                >
                  {sub.label}
                </button>
              ))}
            </div>
          </button>
        )
      })}

      {/* Ver Todos */}
      <button
        onClick={() => setSearchParams({})}
        className="col-span-2 md:col-span-1 group relative flex flex-col items-center justify-center gap-2 p-5 bg-black-deep border border-dashed border-gray-steel/60 text-gray-text cursor-pointer transition-all duration-200 hover:bg-neon-green hover:border-neon-green hover:shadow-[0_0_20px_rgba(0,255,65,0.3)] hover:-translate-y-1"
      >
        <span className="text-2xl group-hover:text-black transition-colors">📋</span>
        <span className="font-mono text-sm font-bold tracking-[0.2em] uppercase group-hover:text-black transition-colors">
          VER TODOS
        </span>
        <span className="font-mono text-base group-hover:text-black transition-colors">→</span>
      </button>
    </div>
  )
}
