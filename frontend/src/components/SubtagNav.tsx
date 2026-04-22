import { useSearchParams } from 'react-router-dom'
import { TAG_CONFIG } from '../data/subtags'

interface SubtagNavProps {
  selectedTag: string
}

export default function SubtagNav({ selectedTag }: SubtagNavProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const tagConfig = TAG_CONFIG[selectedTag]

  if (!tagConfig) return null

  const activeSubtag = searchParams.get('subtag') ?? ''

  function selectSubtag(subtag: string) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      if (subtag) {
        next.set('subtag', subtag)
      } else {
        next.delete('subtag')
      }
      next.delete('page')
      return next
    })
  }

  return (
    <nav className="border-b border-gray-steel mb-6 overflow-x-auto">
      <ul className="flex gap-0 min-w-max">
        {/* All subtags button */}
        <li>
          <button
            onClick={() => selectSubtag('')}
            className={[
              'px-4 py-2 font-mono text-xs font-bold tracking-widest uppercase transition-colors',
              'border-b-2 -mb-px',
              !activeSubtag
                ? 'border-neon-green text-neon-green bg-gray-steel'
                : 'border-transparent text-gray-text hover:text-gray-light hover:border-gray-light',
            ].join(' ')}
          >
            Todos
          </button>
        </li>

        {/* Category subtags */}
        {tagConfig.subtags.map(subtag => {
          const isActive = subtag.value === activeSubtag
          return (
            <li key={subtag.value}>
              <button
                onClick={() => selectSubtag(subtag.value)}
                className={[
                  'px-4 py-2 font-mono text-xs font-bold tracking-widest uppercase transition-colors',
                  'border-b-2 -mb-px',
                  isActive
                    ? 'border-neon-green text-neon-green bg-gray-steel'
                    : 'border-transparent text-gray-text hover:text-gray-light hover:border-gray-light',
                ].join(' ')}
              >
                {subtag.label}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
