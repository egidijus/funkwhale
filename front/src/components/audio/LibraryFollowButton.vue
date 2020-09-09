 <template>
  <button @click.stop="toggle" :class="['ui', 'pink', {'inverted': isApproved || isPending}, {'favorited': isApproved}, 'icon', 'labeled', 'button']">
    <i class="heart icon"></i>
    <translate v-if="isApproved" translate-context="Content/Library/Card.Button.Label/Verb">Unfollow</translate>
    <translate v-else-if="isPending" translate-context="Content/Library/Card.Button.Label/Verb">Cancel follow request</translate>
    <translate v-else translate-context="Content/Library/Card.Button.Label/Verb">Follow</translate>
  </button>
</template>

<script>
export default {
  props: {
    library: {type: Object},
  },
  computed: {
    isPending () {
      return this.follow && this.follow.approved === null
    },
    isApproved () {
      return this.follow && (this.follow.approved === true || (this.follow.approved === null && this.library.privacy_level === 'everyone'))
    },
    follow () {
      return this.$store.getters['libraries/follow'](this.library.uuid)
    }
  },
  methods: {
    toggle () {
      if (this.isApproved || this.isPending) {
        this.$emit('unfollowed')
      } else {
        this.$emit('followed')
      }
      this.$store.dispatch('libraries/toggle', this.library.uuid)
    }
  }


}
</script>
