interface PaginationProps {
  page: number
  pages: number
  total: number
  onPage: (page: number) => void
}

export default function Pagination({ page, pages, total, onPage }: PaginationProps) {
  if (pages <= 1) return null

  return (
    <div className="flex items-center justify-between py-6 border-t border-gray-steel mt-6">
      <button
        onClick={() => onPage(page - 1)}
        disabled={page <= 1}
        className="font-mono text-sm font-bold tracking-widest disabled:opacity-30 disabled:cursor-not-allowed text-gray-light hover:text-neon-green transition-colors px-4 py-2 border border-gray-steel hover:border-neon-green disabled:hover:border-gray-steel disabled:hover:text-gray-light"
      >
        ← ANTERIOR
      </button>

      <span className="font-mono text-sm text-gray-text">
        PÁGINA{' '}
        <span className="text-neon-green font-bold">{page}</span>
        {' '}DE{' '}
        <span className="text-gray-light font-bold">{pages}</span>
        <span className="text-gray-text"> · {total} produtos</span>
      </span>

      <button
        onClick={() => onPage(page + 1)}
        disabled={page >= pages}
        className="font-mono text-sm font-bold tracking-widest disabled:opacity-30 disabled:cursor-not-allowed text-gray-light hover:text-neon-green transition-colors px-4 py-2 border border-gray-steel hover:border-neon-green disabled:hover:border-gray-steel disabled:hover:text-gray-light"
      >
        PRÓXIMO →
      </button>
    </div>
  )
}
