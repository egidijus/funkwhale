<template>
  <div></div>
</template>
<script>
import $ from 'jquery'

export default {
  props: ['message'],
  mounted () {
    let self = this
    let params = {
      context: "#app",
      message: this.message.content,
      showProgress: 'top',
      position: "bottom right",
      progressUp: true,
      onRemove () {
        self.$store.commit("ui/removeMessage", self.message.key)
      },
      ...this.message,
    }
    $("body").toast(params)

    $(".ui.toast.visible").last().attr('role', 'alert')
  }
}
</script>
