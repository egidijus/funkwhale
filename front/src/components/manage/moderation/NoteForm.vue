<template>
  <form class="ui form" @submit.prevent="submit()">
    <div v-if="errors.length > 0" role="alert" class="ui negative message">
      <div class="header"><translate translate-context="Content/Moderation/Error message.Title">Error while submitting note</translate></div>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <div class="field">
      <content-form field-id="change-summary" :required="true" v-model="summary" :rows="3" :placeholder="labels.summaryPlaceholder"></content-form>
    </div>
    <button :class="['ui', {'loading': isLoading}, 'right', 'floated', 'button']" type="submit" :disabled="isLoading">
      <translate translate-context="Content/Moderation/Button.Label/Verb">Add note</translate>
    </button>
  </form>
</template>

<script>
import axios from 'axios'
import showdown from 'showdown'

export default {
  props: {
    target: {required: true},
  },
  data () {
      return {
      markdown: new showdown.Converter(),
      isLoading: false,
      summary: '',
      errors: [],
    }
  },
  computed: {
    labels () {
      return {
        summaryPlaceholder: this.$pgettext('Content/Moderation/Placeholder', 'Describe what actions have been taken, or any other related updates…'),
      }
    },
  },
  methods: {
    submit () {
      let self = this
      this.isLoading = true
      let payload = {
        target: this.target,
        summary: this.summary
      }
      this.errors = []
      axios.post(`manage/moderation/notes/`, payload).then((response) => {
        self.$emit('created', response.data)
        self.summary = ''
        self.isLoading = false
      }, error => {
        self.errors = error.backendErrors
        self.isLoading = false
      })
    },
  }
}
</script>
