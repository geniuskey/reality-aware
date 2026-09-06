<script setup lang="ts">
import { computed } from 'vue'
import { useData, withBase } from 'vitepress'

/**
 * A link to the playground from inside a page.
 *
 * The page reads its own language from the query string rather than from a
 * locale directory, so the link has to carry it, and every page in a locale
 * wants the same one. Asking the locale here is one less thing for prose to get
 * wrong. Clicks are handled in `theme/index.ts`, along with every other link to
 * that page.
 */
const { lang } = useData()

const href = computed(
  () => withBase('/playground') + (lang.value.startsWith('ko') ? '?lang=ko' : '')
)
</script>

<template>
  <a :href="href"><slot /></a>
</template>
