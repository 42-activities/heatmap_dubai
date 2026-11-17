import '@testing-library/jest-dom/vitest'

// jsdom lacks ResizeObserver (needed by Recharts' ResponsiveContainer).
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver
