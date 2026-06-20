#!/usr/bin/env node
// gen_docs_api.mjs — derive the docs/api/ NotebookLM corpus from the English
// root of the VitePress site (docs/site/).
//
// The corpus is the multi-file markdown the `api-docs` capability ships for
// Google NotebookLM upload. It is GENERATED, not hand-authored: this script is
// the single source of truth, and CI verifies the committed docs/api/ matches a
// fresh run (`git diff --exit-code docs/api/`).
//
// Contract enforced here (hard-fail, no partial output):
//   - emit ONLY the pinned file-set (no one-file-per-page fan-out)
//   - each emitted file <= 500_000 characters (NotebookLM per-source limit)
//   - total emitted .md count <= 50 (NotebookLM Free per-notebook limit)
//   - docs/api/cookbook/errors.md MUST contain the literal heading phrase
//     `空 FinalAnswer 與小模型 robustness` plus the literal substrings
//     `ValidationErrorObservation` and `non_empty_final_answer`
//   - corpus is English-only: no *.zhTW.md is ever produced
//
// Usage: node scripts/gen_docs_api.mjs   (run via `npm run docs:api`)
// Exit:  0 = corpus written; 1 = contract violation (nothing written)

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const SRC = join(ROOT, 'docs', 'site')
const OUT = join(ROOT, 'docs', 'api')

const MAX_CHARS = 500_000
const MAX_FILES = 50

// [ source page under docs/site/ , output path under docs/api/ ]
// Output names follow the api-docs pinned file-set; protocols/workflows.md
// (site) maps to protocols/workflow.md (corpus) per the spec.
const MAP = [
  ['overview.md', 'overview.md'],
  ['quickstart.md', 'quickstart.md'],
  ['protocols/skill.md', 'protocols/skill.md'],
  ['protocols/analyzer.md', 'protocols/analyzer.md'],
  ['protocols/validator.md', 'protocols/validator.md'],
  ['protocols/workflows.md', 'protocols/workflow.md'],
  ['protocols/memory.md', 'protocols/memory.md'],
  ['protocols/debug.md', 'protocols/debug.md'],
  ['core/agent.md', 'core/agent.md'],
  ['core/event-stream.md', 'core/event-stream.md'],
  ['core/inspector.md', 'core/inspector.md'],
  ['cookbook/patterns.md', 'cookbook/patterns.md'],
  ['cookbook/errors.md', 'cookbook/errors.md'],
  ['cookbook/tips.md', 'cookbook/tips.md'],
]

// Required verbatim tokens in the corpus errors.md (NotebookLM keyword search).
const ERRORS_REQUIRED = [
  '空 FinalAnswer 與小模型 robustness',
  'ValidationErrorObservation',
  'non_empty_final_answer',
]

function fail(msg) {
  console.error(`[gen_docs_api] CONTRACT VIOLATION: ${msg}`)
  console.error('[gen_docs_api] no corpus written.')
  process.exit(1)
}

// Resolve `<!--@include: path-->` directives by inlining the referenced file,
// relative to the including file's directory. Keeps each corpus file
// self-contained for per-source RAG.
function resolveIncludes(text, baseDir) {
  return text.replace(/<!--\s*@include:\s*(.+?)\s*-->/g, (_, rel) => {
    const p = join(baseDir, rel.trim())
    if (!existsSync(p)) fail(`@include target not found: ${rel} (in ${baseDir})`)
    return resolveIncludes(readFileSync(p, 'utf8'), dirname(p))
  })
}

// Flatten a VitePress markdown page into portable, self-contained Markdown:
// strip YAML frontmatter, <script>/<style> blocks, and VitePress container
// fences (::: tip / ::: warning / :::), keeping the inner prose.
function flatten(text, baseDir) {
  let t = resolveIncludes(text, baseDir)
  t = t.replace(/^---\n[\s\S]*?\n---\n/, '') // frontmatter
  t = t.replace(/<script[\s\S]*?<\/script>/g, '')
  t = t.replace(/<style[\s\S]*?<\/style>/g, '')
  t = t.replace(/^:::.*$/gm, '') // VitePress container fences (open + close)
  t = t.replace(/\n{3,}/g, '\n\n').trimStart()
  if (!t.endsWith('\n')) t += '\n'
  return t
}

// 1) Build every output in memory.
const built = []
for (const [src, out] of MAP) {
  const srcPath = join(SRC, src)
  if (!existsSync(srcPath)) fail(`source page missing: docs/site/${src}`)
  const content = flatten(readFileSync(srcPath, 'utf8'), dirname(srcPath))
  built.push({ out, content })
}

// 2) Validate the contract BEFORE writing anything.
if (built.length > MAX_FILES) fail(`emitting ${built.length} files exceeds the ${MAX_FILES}-source ceiling`)
for (const { out, content } of built) {
  if (content.length > MAX_CHARS) fail(`docs/api/${out} is ${content.length} chars, over the ${MAX_CHARS} limit`)
  if (/\.zhTW\.md$/.test(out)) fail(`corpus must be English-only; refusing ${out}`)
}
const errors = built.find((b) => b.out === 'cookbook/errors.md')
if (!errors) fail('cookbook/errors.md missing from the corpus')
for (const token of ERRORS_REQUIRED) {
  if (!errors.content.includes(token)) fail(`cookbook/errors.md is missing the required token: ${token}`)
}

// 3) All checks passed — write the corpus.
for (const { out, content } of built) {
  const dest = join(OUT, out)
  mkdirSync(dirname(dest), { recursive: true })
  writeFileSync(dest, content, 'utf8')
}

console.log(`[gen_docs_api] wrote ${built.length} files to docs/api/ (max file ${Math.max(...built.map((b) => b.content.length))} chars).`)
