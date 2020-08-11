<template>
  <div>
    <template v-if="content && !isUpdating">
      <div v-html="html"></div>
      <template v-if="isTruncated">
        <div class="ui small hidden divider"></div>
        <a href="" @click.stop.prevent="showMore = true" v-if="showMore === false">
          <translate translate-context="*/*/Button,Label">Show more</translate>
        </a>
        <a href="" @click.stop.prevent="showMore = false" v-else="showMore === true">
          <translate translate-context="*/*/Button,Label">Show less</translate>
        </a>

      </template>
    </template>
    <p v-else-if="!isUpdating">
      <translate translate-context="*/*/Placeholder">No description available</translate>
    </p>
    <template v-if="!isUpdating && canUpdate && updateUrl">
      <div class="ui hidden divider"></div>
      <span role="button" @click="isUpdating = true">
        <i class="pencil icon"></i>
        <translate translate-context="Content/*/Button.Label/Verb">Edit</translate>
      </span>
    </template>
    <form v-if="isUpdating" class="ui form" @submit.prevent="submit()">
      <div v-if="errors.length > 0" role="alert" class="ui negative message">
        <h4 class="header"><translate translate-context="Content/Channels/Error message.Title">Error while updating description</translate></h4>
        <ul class="list">
          <li v-for="error in errors">{{ error }}</li>
        </ul>
      </div>
      <content-form v-model="newText" :autofocus="true"></content-form>
      <a @click.prevent="isUpdating = false" class="left floated">
        <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
      </a>
      <button :class="['ui', {'loading': isLoading}, 'right', 'floated', 'button']" type="submit" :disabled="isLoading">
        <translate translate-context="Content/Channels/Button.Label/Verb">Update description</translate>
      </button>
      <div class="ui clearing hidden divider"></div>
    </form>
  </div>
</template>

<script>
import {secondsToObject} from '@/filters'
import axios from 'axios'
import clip from 'text-clipper'

export default {
  props: {
    content: {required: true},
    fieldName: {required: false, default: 'description'},
    updateUrl: {required: false, type: String},
    canUpdate: {required: false, default: true, type: Boolean},
    fetchHtml: {required: false, default: false, type: Boolean},
    permissive: {required: false, default: false, type: Boolean},
    truncateLength: {required: false, default: 500, type: Number},

  },
  data () {
    return {
      isUpdating: false,
      showMore: false,
      newText: (this.content || {text: ''}).text,
      errors: null,
      isLoading: false,
      errors: [],
      preview: null
    }
  },
  async created () {
    if (this.fetchHtml) {
      await this.fetchPreview()
    }
  },
  computed: {
    html () {
      if (this.fetchHtml) {
        return this.preview
      }
      if (this.truncateLength > 0 && !this.showMore) {
        return this.truncatedHtml
      }
      return this.content.html
    },
    truncatedHtml () {
      return clip(this.content.html, this.truncateLength, { html: true, maxLines: 3 })
    },
    isTruncated () {
      return this.truncateLength > 0 && this.truncatedHtml.length < this.content.html.length
    }
  },
  methods: {
    async fetchPreview () {
      let response = await axios.post('text-preview/', {text: this.content.text, permissive: this.permissive})
      this.preview = response.data.rendered
    },
    submit () {
      let self = this
      this.isLoading = true
      this.errors = []
      let payload = {}
      payload[this.fieldName] = null
      if (this.newText) {
        payload[this.fieldName] = {
          content_type: "text/markdown",
          text: this.newText,
        }
      }
      axios.patch(this.updateUrl, payload).then((response) => {
        self.$emit('updated', response.data)
        self.isLoading = false
        self.isUpdating = false
      }, error => {
        self.errors = error.backendErrors
        self.isLoading = false
      })
    },
  }
}
</script>
