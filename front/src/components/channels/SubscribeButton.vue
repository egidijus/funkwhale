 <template>
  <button @click.stop="toggle" :class="['ui', 'pink', {'inverted': isSubscribed}, {'favorited': isSubscribed}, 'icon', 'labeled', 'button']">
    <i class="heart icon"></i>
    <translate v-if="isSubscribed" translate-context="Content/Track/Button.Message">Unsubscribe</translate>
    <translate v-else translate-context="Content/Track/*/Verb">Subscribe</translate>
  </button>
</template>

<script>
export default {
  props: {
    channel: {type: Object},
  },
  computed: {
    title () {
      if (this.isSubscribed) {
        return this.$pgettext('Content/Channel/Button/Verb', 'Subscribe')
      } else {
        return this.$pgettext('Content/Channel/Button/Verb', 'Unsubscribe')
      }
    },
    isSubscribed () {
      return this.$store.getters['channels/isSubscribed'](this.channel.uuid)
    }
  },
  methods: {
    toggle () {
      if (this.isSubscribed) {
        this.$emit('unsubscribed')
      } else {
        this.$emit('subscribed')
      }
      this.$store.dispatch('channels/toggle', this.channel.uuid)
    }
  }


}
</script>
