import { createApi } from './api'
import { createStatic } from './static'
import type { DataSource } from './types'

// The only env branch in the app: API mode when VITE_API_BASE is set, else static JSON.
const apiBase = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/+$/, '')

export const data: DataSource = apiBase ? createApi(apiBase) : createStatic(import.meta.env.BASE_URL)

export * from './types'
