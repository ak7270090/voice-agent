export function BrandMark() {
  return (
    <div className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-xs text-white">
      <svg viewBox="0 0 32 32" className="h-full w-full" aria-hidden="true">
        <path
          d="M7 13.5v5M11.5 9.5v13M16 6v20M20.5 10.5v11M25 13.5v5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.6"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}
