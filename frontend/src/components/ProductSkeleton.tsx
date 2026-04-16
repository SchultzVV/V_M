export default function ProductSkeleton() {
  return (
    <div className="card-def animate-pulse">
      {/* Image placeholder */}
      <div className="aspect-square bg-gray-steel w-full" />

      <div className="p-4 space-y-3">
        {/* Title */}
        <div className="h-4 bg-gray-steel w-full" />
        <div className="h-4 bg-gray-steel w-3/4" />

        {/* Price */}
        <div className="h-7 bg-gray-steel w-1/2 mt-2" />

        {/* Button */}
        <div className="h-10 bg-gray-steel w-full mt-3" />
      </div>
    </div>
  )
}

export function ProductSkeletonGrid({ count = 20 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-px bg-gray-steel">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-black-deep">
          <ProductSkeleton />
        </div>
      ))}
    </div>
  )
}
