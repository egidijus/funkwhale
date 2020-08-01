<template>
   <span :class="['component-volume-control', {'expanded': expanded}]" @click.prevent.stop="" @mouseover="handleOver" @mouseleave="handleLeave">
    <span
      role="button"
      v-if="sliderVolume === 0"
      :title="labels.unmute"
      :aria-label="labels.unmute"
      @click.prevent.stop="unmute">
      <i class="volume off icon"></i>
    </span>
    <span
      role="button"
      v-else-if="sliderVolume < 0.5"
      :title="labels.mute"
      :aria-label="labels.mute"
      @click.prevent.stop="mute">
      <i class="volume down icon"></i>
    </span>
    <span
      role="button"
      v-else
      :title="labels.mute"
      :aria-label="labels.mute"
      @click.prevent.stop="mute">
      <i class="volume up icon"></i>
    </span>
    <div class="popup">
      <label for="volume-slider" class="visually-hidden">{{ labels.slider }}</label>
      <input
        id="volume-slider"
        type="range"
        step="0.05"
        min="0"
        max="1"
        v-model="sliderVolume" />
    </div>
  </span>
</template>
<script>
import { mapState, mapGetters, mapActions } from "vuex"

export default {
  data () {
    return {
      expanded: false,
      timeout: null,
    }
  },
  computed: {
    sliderVolume: {
      get () {
        return this.$store.state.player.volume
      },
      set (v) {
        this.$store.commit("player/volume", v)
      }
    },
    labels () {
      return {
        unmute: this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Unmute"),
        mute: this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Mute"),
        slider: this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Adjust volume")
      }
    }
  },
  methods: {
    ...mapActions({
      mute: "player/mute",
      unmute: "player/unmute",
      toggleMute: "player/toggleMute",
    }),
    handleOver () {
      if (this.timeout) {
        clearTimeout(this.timeout)
      }
      this.expanded = true
    },
    handleLeave () {
      if (this.timeout) {
        clearTimeout(this.timeout)
      }
      this.timeout = setTimeout(() => {this.expanded = false}, 500)
    }
  }
}
</script>
