<template>
  <span class="feedback" v-if="isLoading || isDone">
    <span v-if="isLoading" :class="['ui', 'active', size, 'inline', 'loader']"></span>
    <i v-if="isDone" :class="['success', size, 'check', 'icon']"></i>
  </span>
</template>

<script>
import {hashCode, intToRGB} from '@/utils/color'

export default {
  props: {
    isLoading: {type: Boolean, required: true},
    size: {type: String, default: 'small'},
  },
  data () {
    return {
      timer: null,
      isDone: false,
    }
  },
  destroyed () {
    if (this.timer) {
      clearTimeout(this.timer)
    }
  },
  watch: {
    isLoading (v) {
      let self = this
      if (v && this.timer) {
        clearTimeout(this.timer)
      }
      if (v) {
        this.isDone = false
      } else {
        this.isDone = true
        this.timer = setTimeout(() => {
          self.isDone = false
        }, (2000));

      }
    }
  }
}
</script>
