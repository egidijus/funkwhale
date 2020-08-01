<template>
  <div class="ui form">
    <div v-if="errors.length > 0" role="alert" class="ui negative message">
      <h4 class="header"><translate translate-context="Content/*/Error message.Title">Your attachment cannot be saved</translate></h4>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <div class="ui field">
      <span id="avatarLabel">
        <slot name="label"></slot>
      </span>
      <div class="ui stackable grid row">
        <div class="three wide column">
          <img alt="" :class="['ui', imageClass, 'image']" v-if="value && value === initialValue" :src="$store.getters['instance/absoluteUrl'](`api/v1/attachments/${value}/proxy?next=medium_square_crop`)" />
          <img alt="" :class="['ui', imageClass, 'image']" v-else-if="attachment" :src="$store.getters['instance/absoluteUrl'](`api/v1/attachments/${attachment.uuid}/proxy?next=medium_square_crop`)" />
          <div :class="['ui', imageClass, 'static', 'large placeholder image']" v-else></div>
        </div>
        <div class="eleven wide column">
          <div class="file-input">
            <label class="ui basic button" :for="attachmentId">
              <translate translate-context="*/*/*">Upload New Picture…</translate>
            </label>
            <input class="ui hidden input" ref="attachment" type="file" :id="attachmentId" accept="image/x-png,image/jpeg" @change="submit" />
          </div>
          <div class="ui very small hidden divider"></div>
          <p><translate translate-context="Content/*/Paragraph">PNG or JPG. Dimensions should be between 1400x1400px and 3000x3000px. Maximum file size allowed is 5MB.</translate></p>
          <div class="ui basic tiny button" v-if="value" @click.stop.prevent="remove(value)">
            <translate translate-context="Content/Radio/Button.Label/Verb">Remove</translate>
          </div>
          <div v-if="isLoading" class="ui active inverted dimmer">
            <div class="ui indeterminate text loader">
              <translate translate-context="Content/*/*/Noun">Uploading file…</translate>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import axios from 'axios'

export default {
  props: {
    value: {},
    imageClass: {default: '', required: false}
  },
  data () {
    return {
      attachment: null,
      isLoading: false,
      errors: [],
      initialValue: this.value,
      attachmentId: Math.random().toString(36).substring(7),
    }
  },
  methods: {
    submit() {
      this.isLoading = true
      this.errors = []
      let self = this
      this.file = this.$refs.attachment.files[0]
      let formData = new FormData()
      formData.append("file", this.file)
      axios
        .post(`attachments/`, formData, {
          headers: {
            "Content-Type": "multipart/form-data"
          }
        })
        .then(
          response => {
            this.isLoading = false
            self.attachment = response.data
            self.$emit('input', self.attachment.uuid)
          },
          error => {
            self.isLoading = false
            self.errors = error.backendErrors
          }
        )
    },
    remove(uuid) {
      this.isLoading = true
      this.errors = []
      let self = this
      axios.delete(`attachments/${uuid}/`)
        .then(
          response => {
            this.isLoading = false
            self.attachment = null
            self.$emit('delete')
          },
          error => {
            self.isLoading = false
            self.errors = error.backendErrors
          }
        )
    },
  },
  watch: {
    value (v) {
      if (this.attachment && v === this.initialValue) {
        // we had a reset to initial value
        this.remove(this.attachment.uuid)
      }
    }
  }
}
</script>
