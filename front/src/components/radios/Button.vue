<template>
  <button @click="toggleRadio" :class="['ui', 'primary', {'inverted': running}, 'icon', 'labeled', 'button']">
    <i class="ui feed icon" role="button"></i>
    <template v-if="running"><translate translate-context="*/Player/Button.Label/Short, Verb">Stop radio</translate></template>
    <template v-else><translate translate-context="*/Queue/Button.Label/Short, Verb">Start radio</translate></template>
  </button>
</template>

<script>

import lodash from '@/lodash'
export default {
  props: {
    customRadioId: {required: false},
    type: {type: String, required: false},
    clientOnly: {type: Boolean, default: false},
    objectId: {default: null}
  },
  methods: {
    toggleRadio () {
      if (this.running) {
        this.$store.dispatch('radios/stop')
      } else {
        this.$store.dispatch('radios/start', {
          type: this.type,
          objectId: this.objectId,
          customRadioId: this.customRadioId,
          clientOnly: this.clientOnly,
        })
      }
    }
  },
  computed: {
    running () {
      let state = this.$store.state.radios
      let current = state.current
      if (!state.running) {
        return false
      } else {
        return current.type === this.type && lodash.isEqual(current.objectId, this.objectId) && current.customRadioId === this.customRadioId
      }
    }
  }
}
</script>
