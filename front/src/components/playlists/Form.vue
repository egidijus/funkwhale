<template>
  <form class="ui form" @submit.prevent="submit()">
    <h4 v-if="title" class="ui header"><translate translate-context="Popup/Playlist/Title/Verb">Create a new playlist</translate></h4>
    <div v-if="success" class="ui positive message">
      <h4 class="header">
        <template v-if="playlist">
          <translate translate-context="Content/Playlist/Message">Playlist updated</translate>
        </template>
        <template v-else>
          <translate translate-context="Content/Playlist/Message">Playlist created</translate>
        </template>
      </h4>
    </div>
    <div v-if="errors.length > 0" role="alert" class="ui negative message">
      <h4 class="header"><translate translate-context="Content/Playlist/Error message.Title">The playlist could not be created</translate></h4>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <div class="three fields">
      <div class="field">
        <label><translate translate-context="Content/Playlist/Input.Label">Playlist name</translate></label>
        <input name="name" v-model="name" required type="text" :placeholder="labels.placeholder" />
      </div>
      <div class="field">
        <label><translate translate-context="Content/Playlist/Dropdown.Label">Playlist visibility</translate></label>
        <select class="ui dropdown" v-model="privacyLevel">
          <option :value="c.value" v-for="c in privacyLevelChoices">{{ c.label }}</option>
        </select>
      </div>
      <div class="field">
        <label>&nbsp;</label>
        <button :class="['ui', 'fluid', {'loading': isLoading}, 'button']" type="submit">
          <template v-if="playlist"><translate translate-context="Content/Playlist/Button.Label/Verb">Update playlist</translate></template>
          <template v-else><translate translate-context="Content/Playlist/Button.Label/Verb">Create playlist</translate></template>
        </button>
      </div>
    </div>
  </form>
</template>

<script>
import $ from 'jquery'
import axios from 'axios'
import TranslationsMixin from "@/components/mixins/Translations"

import logger from '@/logging'

export default {
  mixins: [TranslationsMixin],
  props: {
    title: {type: Boolean, default: true},
    playlist: {type: Object, default: null}
  },
  mounted () {
    $(this.$el).find('.dropdown').dropdown()
  },
  data () {
    let d = {
      errors: [],
      success: false,
      isLoading: false
    }
    if (this.playlist) {
      d.name = this.playlist.name
      d.privacyLevel = this.playlist.privacy_level
    } else {
      d.privacyLevel = this.$store.state.auth.profile.privacy_level
      d.name = ''
    }
    return d
  },
  computed: {
    labels () {
      return {
        placeholder: this.$pgettext('Content/Playlist/Input.Placeholder', 'My awesome playlist')
      }
    },
    privacyLevelChoices: function () {
      return [
        {
          value: 'me',
          label: this.sharedLabels.fields.privacy_level.choices['me']
        },
        {
          value: 'instance',
          label: this.sharedLabels.fields.privacy_level.choices['instance']
        },
        {
          value: 'everyone',
          label: this.sharedLabels.fields.privacy_level.choices['everyone']
        }
      ]
    }
  },
  methods: {
    submit () {
      this.isLoading = true
      this.success = false
      this.errors = []
      let self = this
      let payload = {
        name: this.name,
        privacy_level: this.privacyLevel
      }

      let promise
      let url
      if (this.playlist) {
        url = `playlists/${this.playlist.id}/`
        promise = axios.patch(url, payload)
      } else {
        url = 'playlists/'
        promise = axios.post(url, payload)
      }
      return promise.then(response => {
        self.success = true
        self.isLoading = false
        if (!self.playlist) {
          self.name = ''
        }
        self.$emit('updated', response.data)
        self.$store.dispatch('playlists/fetchOwn')
      }, error => {
        logger.default.error('Error while creating playlist')
        self.isLoading = false
        self.errors = error.backendErrors
      })
    }
  }
}
</script>
