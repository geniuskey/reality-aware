<script setup lang="ts">
import { computed } from 'vue'
import { withBase } from 'vitepress'
import { data as assets } from '../../data/assets.data.mts'
import { useStrings } from '../i18n'

/**
 * Renders a figure produced by the benchmark, or an explicit pending state when
 * the file has not been generated. Paths go through withBase() so project Pages
 * (/<repo>/) and user Pages (/) both resolve correctly.
 */
const props = defineProps<{
  file: string
  title: string
  caption: string
  /** How the figure is produced, so a reader can trace it back to code. */
  producedBy?: string
}>()

const t = useStrings()

const exists = computed(() => assets.files.includes(props.file))
const src = computed(() => withBase(`/results/${props.file}`))
const isVideo = computed(() => /\.(mp4|webm)$/i.test(props.file))
</script>

<template>
  <figure v-if="exists" class="nano-figure nano-asset">
    <video v-if="isVideo" :src="src" controls playsinline loop muted :aria-label="caption" />
    <img v-else :src="src" :alt="caption" loading="lazy" />
    <figcaption>
      <strong>{{ title }}</strong> — {{ caption }}
      <span class="nano-asset__src">
        <code>{{ assets.dir }}/{{ file }}</code><template v-if="producedBy">
          · {{ t.asset.producedBy }} <code>{{ producedBy }}</code></template>
      </span>
    </figcaption>
  </figure>

  <div v-else class="nano-empty">
    <span class="nano-tag" data-kind="pending">{{ t.pending }}</span>
    <p><strong>{{ title }}</strong> — {{ caption }}</p>
    <p class="nano-note">
      {{ t.asset.expectedAt }}: <code>{{ assets.dir }}/{{ file }}</code><template v-if="producedBy">,
      {{ t.asset.expectedProducedBy }} <code>{{ producedBy }}</code></template>.
      {{ t.asset.nothingDrawn }}
    </p>
  </div>
</template>

<style scoped>
.nano-asset img,
.nano-asset video {
  display: block;
  width: 100%;
  height: auto;
  background: var(--nano-surface);
  border: 1px solid var(--nano-border);
  border-radius: var(--nano-radius);
}

.nano-asset__src {
  display: block;
  margin-top: 0.3rem;
  font-size: 0.78rem;
}

.nano-empty {
  background: var(--nano-surface);
  border: 1px dashed var(--nano-border);
  border-radius: var(--nano-radius);
  padding: 1.25rem;
  margin: 1.75rem 0;
}

.nano-empty p {
  margin: 0.7rem 0 0;
  font-size: 0.9rem;
  color: var(--nano-text-dim);
}
</style>
