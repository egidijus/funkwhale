<template>
  <div class="ui card">
    <div class="content">
      <h4 class="header">
        {{ library.name }}
        <span
          v-if="library.privacy_level === 'me'"
          class="right floated"
          :data-tooltip="privacy_tooltips('me')">
          <i class="small lock icon"></i>
        </span>
        <span
          v-else-if="library.privacy_level === 'instance'"
          class="right floated"
          :data-tooltip="privacy_tooltips('instance')">
          <i class="small circle outline icon"></i>
        </span>
        <span
          v-else-if="library.privacy_level === 'everyone'"
          class="right floated"
          :data-tooltip="privacy_tooltips('everyone')">
          <i class="small globe icon"></i>
        </span>
      </h4>
      <div class="meta">
        <span>
          <i class="small outline clock icon" />
          <human-date :date="library.creation_date" />
        </span>
      </div>
      <div class="description">
        {{ library.description }}
        <div class="ui hidden divider"></div>
      </div>
      <div class="content">
        <span v-if="library.size" class="right floated" :data-tooltip="size_label">
          <i class="database icon"></i>
          {{ library.size | humanSize }}
        </span>
        <i class="music icon"></i>
        <translate translate-context="*/*/*" :translate-params="{count: library.uploads_count}" :translate-n="library.uploads_count" translate-plural="%{ count } tracks">%{ count } track</translate>
      </div>
    </div>
    <div class="ui bottom basic attached buttons">
      <router-link :to="{name: 'library.detail.upload', params: {id: library.uuid}}" class="ui button">
        <translate translate-context="Content/Library/Card.Button.Label/Verb">Upload</translate>
      </router-link>
      <router-link :to="{name: 'library.detail', params: {id: library.uuid}}" exact class="ui button">
        <translate translate-context="Content/Library/Card.Button.Label/Noun">Details</translate>
      </router-link>
    </div>
  </div>
</template>

<script>
import TranslationsMixin from '@/components/mixins/Translations'

export default {
  mixins: [TranslationsMixin],
  props: ['library'],
  methods: {
    privacy_tooltips (level) {
      return 'Visibility: ' + this.sharedLabels.fields.privacy_level.choices[level].toLowerCase()
    },
  },
  computed: {
    size_label () {
      return this.$pgettext('Content/Library/Card.Help text', 'Total size of the files in this library')
    },
  }
}
</script>
