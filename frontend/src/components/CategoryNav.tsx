import { useSearchParams } from 'react-router-dom'

interface Category {
  label: string
  value: string
}

const CATEGORIES: Category[] = [
  { label: 'TODOS', value: '' },
  { label: 'PET', value: 'PET' },
  { label: 'ELETRÔNICOS', value: 'E' },
  { label: 'CASA', value: 'CD' },
  { label: 'MODA', value: 'ME' },
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
