<template>
  <modal @update:show="update" :show="$store.state.moderation.showFilterModal">
    <div class="header">
      <translate
        v-if="type === 'artist'"
        key="1"
        translate-context="Popup/Moderation/Title/Verb"
        :translate-params="{name: target.name}">Do you want to hide content from artist "%{ name }"?</translate>
    </div>
    <div class="scrolling content">
      <div class="description">

        <div v-if="errors.length > 0" role="alert" class="ui negative message">
          <div class="header"><translate translate-context="Popup/Moderation/Error message">Error while creating filter</translate></div>
          <ul class="list">
            <li v-for="error in errors">{{ error }}</li>
          </ul>
        </div>
        <template v-if="type === 'artist'">
          <p>
            <translate translate-context="Popup/Moderation/Paragraph">
              You will not see tracks, albums and user activity linked to this artist any more:
            </translate>
          </p>
          <ul>
            <li><translate translate-context="Popup/Moderation/List item">In other users favorites and listening history</translate></li>
            <li><translate translate-context="Popup/Moderation/List item">In "Recently added" widget</translate></li>
            <li><translate translate-context="Popup/Moderation/List item">In artists and album listings</translate></li>
            <li><translate translate-context="Popup/Moderation/List item">In radio suggestions</translate></li>
          </ul>
          <p>
            <translate translate-context="Popup/Moderation/Paragraph">
              You can manage and update your filters any time from your account settings.
            </translate>
          </p>
        </template>
      </div>
    </div>
    <div class="actions">
      <div class="ui basic cancel button"><translate translate-context="*/*/Button.Label/Verb">Cancel</translate></div>
      <div :class="['ui', 'green', {loading: isLoading}, 'button']" @click="hide"><translate translate-context="Popup/*/Button.Label">Hide content</translate></div>
    </div>
  </modal>
</template>

<script>
import _ from '@/lodash'
import axios from 'axios'
import {mapState} from 'vuex'

import logger from '@/logging'
import Modal from '@/components/semantic/Modal'

export default {
  components: {
    Modal,
  },
  data () {
    return {
      formKey: String(new Date()),
      errors: [],
      isLoading: false
    }
  },
  computed: {
    ...mapState({
      type: state => state.moderation.filterModalTarget.type,
      target: state => state.moderation.filterModalTarget.target,
    })
  },
  methods: {
    update (v) {
      this.$store.commit('moderation/showFilterModal', v)
      this.errors = []
    },
    hide () {
      let self = this
      self.isLoading = true
      let payload = {
        target: {
          type: this.type,
          id: this.target.id,
        }
      }
      return axios.post('moderation/content-filters/', payload).then(response => {
        logger.default.info('Successfully added track to playlist')
        self.update(false)
        self.$store.commit('moderation/lastUpdate', new Date())
        self.isLoading = false
        let msg = this.$pgettext('*/Moderation/Message', 'Content filter successfully added')
        self.$store.commit('moderation/contentFilter', response.data)
        self.$store.commit('ui/addMessage', {
          content: msg,
          date: new Date()
        })
      }, error => {
        logger.default.error(`Error while hiding ${self.type} ${self.target.id}`)
        self.errors = error.backendErrors
        self.isLoading = false
      })
    }
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
</style>
