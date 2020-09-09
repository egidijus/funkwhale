<template>
  <div class="component-tags-list">
    <router-link
      :to="{name: detailRoute, params: {id: tag}}"
      :class="['ui', 'circular', 'hashtag', 'label', labelClasses]"
      v-for="tag in toDisplay"
      :key="tag">
      #{{ tag|truncate(truncateSize) }}
    </router-link>
    <div role="button" @click.prevent="honorLimit = false" class="ui circular inverted accent label" v-if="showMore && toDisplay.length < tags.length">
      <translate translate-context="Content/*/Button/Label/Verb" :translate-params="{count: tags.length - toDisplay.length}" :translate-n="tags.length - toDisplay.length" translate-plural="Show %{ count } more tags">Show 1 more tag</translate>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    tags: {type: Array, required: true},
    showMore: {type: Boolean, default: true},
    truncateSize: {type: Number, default: 25},
    limit: {type: Number, default: 5},
    labelClasses: {type: String, default: ''},
    detailRoute: {type: String, default: 'library.tags.detail'},
  },
  data () {
    return {
      honorLimit: true,
    }
  },
  computed: {
    toDisplay () {
      if (!this.honorLimit) {
        return this.tags
      }
      return (this.tags || []).slice(0, this.limit)
    }
  }
}
</script>
