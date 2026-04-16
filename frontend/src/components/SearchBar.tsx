import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'

const DEBOUNCE_MS = 400

interface SearchBarProps {
  hero?: boolean
}

export default function SearchBar({ hero = false }: SearchBarProps) {
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

  if (hero) {
    return (
      <div className="relative w-full group">
        {/* Icon */}
        <span className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-text group-focus-within:text-neon-green transition-colors duration-200 pointer-events-none">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
        </span>
        <input
          ref={inputRef}
          type="text"
          defaultValue={currentSearch}
          onChange={handleChange}
          placeholder="BUSCAR PRODUTO, CATEGORIA, MARCA..."
          className="
            w-full bg-[#0d0d0d] border-2 border-gray-steel
            focus:border-neon-green focus:shadow-[0_0_0_1px_theme(colors.neon-green),0_0_24px_theme(colors.neon-green/20%)]
            text-gray-light font-mono text-base tracking-wide
            pl-14 pr-14 py-4
            outline-none placeholder:text-gray-text/50 placeholder:tracking-wider
            transition-all duration-200
          "
          aria-label="Buscar produto"
        />
        {currentSearch && (
          <button
            onClick={handleClear}
            className="absolute right-5 top-1/2 -translate-y-1/2 text-gray-text hover:text-neon-red font-mono text-base transition-colors"
            aria-label="Limpar busca"
          >
            ✕
          </button>
        )}
        {/* Bottom accent line */}
        <div className="absolute bottom-0 left-0 h-[2px] w-0 bg-neon-green group-focus-within:w-full transition-all duration-300" />
      </div>
    )
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

