import { useSearchParams } from 'react-router-dom'
import { TAG_CONFIG } from '../data/subtags'

const TAGS = ['PET', 'E', 'CD', 'ME'] as const

export default function CatalogNav() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTag = searchParams.get('tag') ?? ''
  const activeSubtag = searchParams.get('subtag') ?? ''

  function selectAll() {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.delete('tag')
      next.delete('subtag')
      next.delete('page')
      return next
    })
  }

  function selectTag(tag: string) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('tag', tag)
      next.delete('subtag')
      next.delete('page')
      return next
    })
  }

  function selectSubtag(tag: string, subtag: string) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('tag', tag)
      next.set('subtag', subtag)
      next.delete('page')
      return next
    })
  }

  const isAll = !activeTag

  return (
    <nav className="mb-6 border border-gray-steel bg-black-deep">
      {/* TODOS row */}
      <div className="px-4 py-2.5 border-b border-gray-steel flex items-center">
        <button
          onClick={selectAll}
          className={[
            'font-mono text-xs font-bold tracking-[0.2em] uppercase transition-colors',
            isAll
              ? 'text-neon-red'
              : 'text-gray-text hover:text-gray-light',
          ].join(' ')}
        >
          ← TODOS
        </button>
      </div>

      {/* Category + Subtag rows */}
      {TAGS.map((tagKey, i) => {
        const config = TAG_CONFIG[tagKey]
        const tagActive = activeTag === tagKey

        return (
          <div
            key={tagKey}
            className={[
              'flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3',
              i < TAGS.length - 1 ? 'border-b border-gray-steel/40' : '',
              tagActive ? 'bg-gray-steel/10' : '',
            ].join(' ')}
          >
            {/* Category label — 1 clique = filtra categoria */}
            <button
              onClick={() => selectTag(tagKey)}
              className={[
                'font-mono text-xs font-bold tracking-[0.18em] uppercase w-28 shrink-0 text-left transition-colors',
                tagActive && !activeSubtag
                  ? 'text-neon-red'
                  : tagActive
                    ? 'text-gray-light'
                    : 'text-gray-text hover:text-gray-light',
              ].join(' ')}
            >
              {config.label}
            </button>

            {/* Subtag chips — 1 clique = filtra subtag diretamente */}
            <div className="flex flex-wrap gap-1.5">
              {config.subtags.map(sub => {
                const isActive = tagActive && activeSubtag === sub.value
                return (
                  <button
                    key={sub.value}
                    onClick={() => selectSubtag(tagKey, sub.value)}
                    className={[
                      'font-mono text-[10px] font-bold tracking-widest uppercase px-2.5 py-1 border transition-all duration-150',
                      isActive
                        ? 'border-neon-green text-neon-green bg-gray-steel shadow-[0_0_8px_rgba(0,255,65,0.25)]'
                        : 'border-gray-steel/50 text-gray-text hover:border-gray-light hover:text-gray-light',
                    ].join(' ')}
                  >
                    {sub.label}
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
    </nav>
  )
}
