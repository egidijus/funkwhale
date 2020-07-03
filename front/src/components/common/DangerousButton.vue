<template>
  <div @click="showModal = true" :class="[{disabled: disabled}]" role="button" :disabled="disabled">
    <slot></slot>

    <modal class="small" :show.sync="showModal">
      <h4 class="header">
        <slot name="modal-header">
          <translate translate-context="Modal/*/Title">Do you want to confirm this action?</translate>
        </slot>
      </h4>
      <div class="scrolling content">
        <div class="description">
          <slot name="modal-content"></slot>
        </div>
      </div>
      <div class="actions">
        <button class="ui basic cancel button">
          <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
        </button>
        <button :class="['ui', 'confirm', confirmButtonColor, 'button']" @click="confirm">
          <slot name="modal-confirm">
            <translate translate-context="Modal/*/Button.Label/Short, Verb">Confirm</translate>
          </slot>
        </button>
      </div>
    </modal>
  </div>

</template>
<script>
import Modal from '@/components/semantic/Modal'

export default {
  props: {
    action: {type: Function, required: false},
    disabled: {type: Boolean, default: false},
    confirmColor: {type: String, default: "danger", required: false}
  },
  components: {
    Modal
  },
  data () {
    return {
      showModal: false
    }
  },
  computed: {
    confirmButtonColor () {
      if (this.confirmColor) {
        return this.confirmColor
      }
      return this.color
    }
  },
  methods: {
    confirm () {
      this.showModal = false
      this.$emit('confirm')
      if (this.action) {
        this.action()
      }
    }
  }
}
</script>
