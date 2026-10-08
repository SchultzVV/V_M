import { useSearchParams } from 'react-router-dom'
import { TAG_CONFIG } from '../data/subtags'

interface Category {
  label: string
  value: string
}

const CATEGORIES: Category[] = [
  { label: 'TODOS', value: '' },
  { label: TAG_CONFIG.PET.label, value: 'PET' },
  { label: TAG_CONFIG.E.label, value: 'E' },
  { label: TAG_CONFIG.CD.label, value: 'CD' },
  { label: TAG_CONFIG.ME.label, value: 'ME' },
  { label: TAG_CONFIG.ES.label, value: 'ES' },
]

export default function CategoryNav() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTag = searchParams.get('tag') ?? ''

  function selectCategory(value: string) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      if (value) {
        next.set('tag', value)
      } else {
        next.delete('tag')
      }
      next.delete('page')
      return next
    })
  }

  return (
    <nav className="border-b border-gray-steel mb-6 overflow-x-auto">
      <ul className="flex gap-0 min-w-max">
        {CATEGORIES.map(cat => {
          const isActive = cat.value === activeTag
          return (
            <li key={cat.value}>
              <button
                onClick={() => selectCategory(cat.value)}
                className={[
                  'px-5 py-3 font-mono text-sm font-bold tracking-widest uppercase transition-colors',
                  'border-b-2 -mb-px',
                  isActive
                    ? 'border-neon-red text-neon-red bg-gray-steel'
                    : 'border-transparent text-gray-text hover:text-gray-light hover:border-gray-light',
                ].join(' ')}
              >
                {cat.label}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
