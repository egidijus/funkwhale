 <template>
  <button @click.stop="$store.dispatch('favorites/toggle', track.id)" v-if="button" :class="['ui', 'pink', {'inverted': isFavorite}, {'favorited': isFavorite}, 'icon', 'labeled', 'button']">
    <i class="heart icon"></i>
    <translate v-if="isFavorite" translate-context="Content/Track/Button.Message">In favorites</translate>
    <translate v-else translate-context="Content/Track/*/Verb">Add to favorites</translate>
  </button>
  <button
    v-else
    @click.stop="$store.dispatch('favorites/toggle', track.id)"
    :class="['ui', 'favorite-icon', {'pink': isFavorite}, {'favorited': isFavorite}, 'basic', 'circular', 'icon', {'really': !border}, 'button']"
    :aria-label="title"
    :title="title">
    <i :class="['heart', {'pink': isFavorite}, 'basic', 'icon']"></i>
  </button>
</template>

<script>
export default {
  props: {
    track: {type: Object},
    button: {type: Boolean, default: false},
    border: {type: Boolean, default: false},
  },
  computed: {
    title () {
      if (this.isFavorite) {
        return this.$pgettext('Content/Track/Icon.Tooltip/Verb', 'Remove from favorites')
      } else {
        return this.$pgettext('Content/Track/*/Verb', 'Add to favorites')
      }
    },
    isFavorite () {
      return this.$store.getters['favorites/isFavorite'](this.track.id)
    }
  }

}
</script>
