import type { SVGProps } from "react"

type IconProps = { size?: number; className?: string }

function Svg({ size = 16, className, children, ...rest }: IconProps & SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
      {...rest}
    >
      {children}
    </svg>
  )
}

export function ArrowRight(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 12h14M13 5l7 7-7 7" />
    </Svg>
  )
}

export function ArrowUpRight(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M7 17 17 7M8 7h9v9" />
    </Svg>
  )
}

export function ArrowUp(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </Svg>
  )
}

export function ArrowDown(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 5v14M19 12l-7 7-7-7" />
    </Svg>
  )
}

export function TrendUp(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M15 7h6v6" />
    </Svg>
  )
}

export function TrendDown(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 7l6 6 4-4 8 8" />
      <path d="M15 17h6v-6" />
    </Svg>
  )
}

export function Wallet(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2" />
      <rect x="3" y="7" width="18" height="12" />
      <path d="M16 13h2" />
    </Svg>
  )
}

export function ChartLine(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 3v18h18" />
      <path d="M7 15l4-6 3 3 5-7" />
    </Svg>
  )
}

export function Coins(props: IconProps) {
  return (
    <Svg {...props}>
      <ellipse cx="12" cy="6" rx="8" ry="3" />
      <path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6" />
      <path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
    </Svg>
  )
}

export function Percent(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M19 5 5 19" />
      <circle cx="7.5" cy="7.5" r="2.5" />
      <circle cx="16.5" cy="16.5" r="2.5" />
    </Svg>
  )
}

export function Bank(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 10l9-6 9 6" />
      <path d="M4 10v10h16V10" />
      <path d="M8 20v-6M12 20v-6M16 20v-6" />
    </Svg>
  )
}

export function Scale(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3v18" />
      <path d="M5 7h14" />
      <path d="M7 7l-4 7h8L7 7z" />
      <path d="M17 7l-4 7h8l-4-7z" />
    </Svg>
  )
}

export function Lock(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="5" y="11" width="14" height="10" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </Svg>
  )
}

export function CircleHalf(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none" />
    </Svg>
  )
}

export function GitHub(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M9 19c-4 1.5-4-2-6-2m12 4v-3.9a3.4 3.4 0 0 0-1-2.6c3-.3 5-1.8 5-5.9a4.6 4.6 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1.4-.4-4.4 1.7a11 11 0 0 0-5.8 0C4.4 1.8 3 2.2 3 2.2a4.3 4.3 0 0 0-.1 3.2A4.6 4.6 0 0 0 1.6 8.6c0 4 2 5.6 5 5.9a3.4 3.4 0 0 0-1 2.6V21" />
    </Svg>
  )
}

export function LinkedIn(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 9v10M6 5v.01" />
      <path d="M11 19v-6a3 3 0 0 1 6 0v6" />
      <path d="M11 9v10" />
    </Svg>
  )
}
