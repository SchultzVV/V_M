import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'

const DEBOUNCE_MS = 400

export default function SearchBar() {
  const [searchParams, setSearchParams] = useSearchParams()
  const currentSearch = searchParams.get('search') ?? ''
  const inputRef = useRef<HTMLInputElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync input value if URL changes externally (e.g. browser back)
  useEffect(() => {
    if (inputRef.current && inputRef.current.value !== currentSearch) {
      inputRef.current.value = currentSearch
    }
  }, [currentSearch])

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setSearchParams(prev => {
        const next = new URLSearchParams(prev)
        if (value.trim()) {
          next.set('search', value.trim())
        } else {
          next.delete('search')
        }
        next.delete('page')
        return next
      })
    }, DEBOUNCE_MS)
  }

  function handleClear() {
    if (timerRef.current) clearTimeout(timerRef.current)
    if (inputRef.current) inputRef.current.value = ''
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.delete('search')
      next.delete('page')
      return next
    })
  }

  return (
    <div className="relative w-full max-w-md">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-text font-mono text-sm select-none">
        /
      </span>
      <input
        ref={inputRef}
        type="text"
        defaultValue={currentSearch}
        onChange={handleChange}
        placeholder="BUSCAR PRODUTO..."
        className="w-full bg-gray-steel border border-gray-steel focus:border-neon-green text-gray-light font-mono text-sm pl-7 pr-8 py-2 outline-none placeholder:text-gray-text transition-colors"
        aria-label="Buscar produto"
      />
      {currentSearch && (
        <button
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-text hover:text-neon-red font-mono text-sm"
          aria-label="Limpar busca"
        >
          ✕
        </button>
      )}
    </div>
  )
}
