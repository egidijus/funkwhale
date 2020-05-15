<template>
  <form class="ui form" @submit.prevent="submit">
    <p v-if="!library"><translate translate-context="Content/Library/Paragraph">Libraries help you organize and share your music collections. You can upload your own music collection to Funkwhale and share it with your friends and family.</translate></p>
    <div v-if="errors.length > 0" class="ui negative message">
      <div class="header"><translate translate-context="Content/*/Error message.Title">Error</translate></div>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <div class="required field">
      <label><translate translate-context="*/*/*/Noun">Name</translate></label>
      <input name="name" v-model="currentName" :placeholder="labels.namePlaceholder" required maxlength="100">
    </div>
    <div class="field">
      <label><translate translate-context="*/*/*/Noun">Description</translate></label>
      <textarea v-model="currentDescription" :placeholder="labels.descriptionPlaceholder" maxlength="2000"></textarea>
    </div>
    <div class="field">
      <label><translate translate-context="*/*/*">Visibility</translate></label>
      <p><translate translate-context="Content/Library/Paragraph">You are able to share your library with other people, regardless of its visibility.</translate></p>
      <select class="ui dropdown" v-model="currentVisibilityLevel">
        <option :value="c" v-for="c in ['me', 'instance', 'everyone']">{{ sharedLabels.fields.privacy_level.choices[c] }}</option>
      </select>
    </div>
    <button class="ui submit button" type="submit">
      <translate translate-context="Content/Library/Button.Label/Verb" v-if="library">Update library</translate>
      <translate translate-context="Content/Library/Button.Label/Verb" v-else>Create library</translate>
    </button>
    <dangerous-button v-if="library" class="ui right floated basic danger button" @confirm="remove()">
      <translate translate-context="*/*/*/Verb">Delete</translate>
      <p slot="modal-header">
        <translate translate-context="Popup/Library/Title">Delete this library?</translate>
      </p>
      <p slot="modal-content">
        <translate translate-context="Popup/Library/Paragraph">
          The library and all its tracks will be deleted. This can not be undone.
        </translate>
      </p>
      <div slot="modal-confirm">
        <translate translate-context="Popup/Library/Button.Label/Verb">Delete library</translate>
      </div>
    </dangerous-button>
  </form>
</template>

<script>
import axios from 'axios'
import MixinsTranslation from '@/components/mixins/Translations.vue'

export default {
  mixins: [MixinsTranslation],
  props: ['library'],
  data () {
    let d = {
      isLoading: false,
      over: false,
      errors: []
    }
    if (this.library) {
      d.currentVisibilityLevel = this.library.privacy_level
      d.currentName = this.library.name
      d.currentDescription = this.library.description
    } else {
      d.currentVisibilityLevel = 'me'
      d.currentName = ''
      d.currentDescription = ''
    }
    return d
  },
  computed: {
    labels () {
      let namePlaceholder = this.$pgettext('Content/Library/Input.Placeholder', 'My awesome library')
      let descriptionPlaceholder = this.$pgettext('Content/Library/Input.Placeholder', 'This library contains my personal music, I hope you like it.')
      return {
        namePlaceholder,
        descriptionPlaceholder,
      }
    }
  },
  methods: {
    submit () {
      let self = this
      this.isLoading = true
      let payload = {
        name: this.currentName,
        description: this.currentDescription,
        privacy_level: this.currentVisibilityLevel
      }
      let promise
      if (this.library) {
        promise = axios.patch(`libraries/${this.library.uuid}/`, payload)
      } else {
        promise = axios.post('libraries/', payload)
      }
      promise.then((response) => {
        self.isLoading = false
        let msg
        if (self.library) {
          self.$emit('updated', response.data)
          msg = this.$pgettext('Content/Library/Message', 'Library updated')
        } else {
          self.$emit('created', response.data)
          msg = this.$pgettext('Content/Library/Message', 'Library created')
        }
        self.$store.commit('ui/addMessage', {
          content: msg,
          date: new Date()
        })
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    reset () {
      this.currentVisibilityLevel = 'me'
      this.currentName = ''
      this.currentDescription = ''
    },
    remove () {
      let self = this
      axios.delete(`libraries/${this.library.uuid}/`).then((response) => {
        self.isLoading = false
        let msg = this.$pgettext('Content/Library/Message', 'Library deleted')
        self.$emit('deleted', {})
        self.$store.commit('ui/addMessage', {
          content: msg,
          date: new Date()
        })
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    }
  }
}
</script>
