import { defineConfig } from 'vitepress'

// Shared sidebar/nav builders so the English root locale and the zh-tw locale
// stay structurally identical. `base` is '' for the English root and '/zh-tw'
// for the Traditional Chinese locale; pages live under docs/site/ and
// docs/site/zh-tw/ respectively (VitePress directory-based i18n).
function sidebar(base: string) {
  return [
    {
      text: 'Getting Started',
      items: [
        { text: 'Overview', link: `${base}/overview` },
        { text: 'Quickstart (Colab)', link: `${base}/quickstart` },
        { text: 'Quickstart (Desktop)', link: `${base}/quickstart-desktop` },
        { text: 'Terminal UI', link: `${base}/tui` },
      ],
    },
    {
      text: 'Core Runtime',
      items: [
        { text: 'Agent loop', link: `${base}/core/agent` },
        { text: 'Event stream', link: `${base}/core/event-stream` },
        { text: 'Inspector', link: `${base}/core/inspector` },
      ],
    },
    {
      text: 'Protocols',
      items: [
        { text: 'Skill', link: `${base}/protocols/skill` },
        { text: 'Memory', link: `${base}/protocols/memory` },
        { text: 'Analyzer', link: `${base}/protocols/analyzer` },
        { text: 'Validator', link: `${base}/protocols/validator` },
        { text: 'Workflows', link: `${base}/protocols/workflows` },
        { text: 'Debug', link: `${base}/protocols/debug` },
        { text: 'Identity (Soul)', link: `${base}/protocols/identity` },
        { text: 'Serve (HTTP)', link: `${base}/protocols/serve` },
        { text: 'Adapters', link: `${base}/protocols/adapters` },
      ],
    },
    {
      text: 'Model Providers',
      items: [{ text: 'Providers', link: `${base}/model-providers` }],
    },
    {
      text: 'Cookbook',
      items: [
        { text: 'Patterns', link: `${base}/cookbook/patterns` },
        { text: 'Errors & recovery', link: `${base}/cookbook/errors` },
        { text: 'Teaching tips', link: `${base}/cookbook/tips` },
      ],
    },
    {
      text: 'Channels',
      items: [
        { text: 'LINE', link: `${base}/channels/line` },
        { text: 'Telegram', link: `${base}/channels/telegram` },
        { text: 'Discord', link: `${base}/channels/discord` },
        { text: 'Google Chat', link: `${base}/channels/google-chat` },
      ],
    },
  ]
}

function nav(base: string) {
  return [
    { text: 'Overview', link: `${base}/overview` },
    { text: 'Quickstart', link: `${base}/quickstart` },
    { text: 'Protocols', link: `${base}/protocols/skill` },
    { text: 'Interactive manual', link: '/interactive/', target: '_blank', rel: 'noopener' },
    {
      text: 'Links',
      items: [
        { text: 'GitHub', link: 'https://github.com/schola-cantorum/cantus' },
        { text: 'PyPI', link: 'https://pypi.org/project/cantus-agent/' },
      ],
    },
  ]
}

export default defineConfig({
  title: 'Cantus',
  description:
    'A polyphonic framework for composing LLM agent harnesses — teaching-oriented, Colab-first.',
  cleanUrls: true,
  // Migrated content carries relative links that are tightened in later
  // iterations; do not fail the build on dead links while the corpus moves.
  ignoreDeadLinks: true,
  // The interactive manual is mirrored into docs/site/public/interactive/ and
  // served verbatim at /interactive/; it is not a VitePress page.
  locales: {
    root: {
      label: 'English',
      lang: 'en',
      themeConfig: {
        nav: nav(''),
        sidebar: sidebar(''),
      },
    },
    'zh-tw': {
      label: '繁體中文（台灣）',
      lang: 'zh-TW',
      link: '/zh-tw/',
      themeConfig: {
        nav: nav('/zh-tw'),
        sidebar: sidebar('/zh-tw'),
      },
    },
  },
  themeConfig: {
    socialLinks: [
      { icon: 'github', link: 'https://github.com/schola-cantorum/cantus' },
    ],
    search: { provider: 'local' },
  },
})
