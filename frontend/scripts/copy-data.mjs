// Copies ../web/data/* into public/data/ so static mode can serve them. Output is git-ignored.
import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const src = resolve(root, '../web/data')
const dest = resolve(root, 'public/data')

if (!existsSync(src)) {
  console.error(`copy-data: source not found: ${src}`)
  process.exit(1)
}
rmSync(dest, { recursive: true, force: true })
mkdirSync(dest, { recursive: true })
cpSync(src, dest, { recursive: true })
console.log(`copy-data: ${src} -> ${dest}`)
