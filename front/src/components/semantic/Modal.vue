<template>
  <div :class="['ui', {'active': show}, {'overlay fullscreen': fullscreen && ['phone', 'tablet'].indexOf($store.getters['ui/windowSize']) > -1},'modal']">
    <i class="close inside icon"></i>
    <slot v-if="show">

    </slot>
  </div>
</template>

<script>
import $ from 'jquery'
import createFocusTrap from 'focus-trap'

export default {
  props: {
    show: {type: Boolean, required: true},
    fullscreen: {type: Boolean, default: true},
  },
  data () {
    return {
      control: null,
      focusTrap: null,
    }
  },
  mounted () {
    this.focusTrap = createFocusTrap(this.$el)
  },
  beforeDestroy () {
    if (this.control) {
      $(this.$el).modal('hide')
    }
    $(this.$el).remove()
  },
  methods: {
    initModal () {
      this.control = $(this.$el).modal({
        duration: 100,
        onApprove: function () {
          this.$emit('approved')
        }.bind(this),
        onDeny: function () {
          this.$emit('deny')
        }.bind(this),
        onHidden: function () {
          this.$emit('update:show', false)
          this.focusTrap.pause()
        }.bind(this),
        onVisible: function () {
          this.focusTrap.activate()
          this.focusTrap.unpause()
        }.bind(this)
      })
    }
  },
  watch: {
    show: {
      handler (newValue) {
        if (newValue) {
          this.initModal()
          this.$emit('show')
          this.control.modal('show')
        } else {
          if (this.control) {
            this.$emit('hide')
            this.control.modal('hide')
            this.control.remove()
          }
        }
      }
    }
  }

}
</script>
