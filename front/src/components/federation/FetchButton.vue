<template>
  <div @click="createFetch" role="button">
    <div>
      <slot></slot>
    </div>
    <modal class="small" :show.sync="showModal">
      <h3 class="header">
        <translate translate-context="Popup/*/Title">Refreshing object from remote…</translate>
      </h3>
      <div class="scrolling content">
        <template v-if="fetch && fetch.status != 'pending'">
          <div v-if="fetch.status === 'skipped'" class="ui message">
            <div class="header"><translate translate-context="Popup/*/Message.Title">Refresh was skipped</translate></div>
            <p><translate translate-context="Popup/*/Message.Content">The remote server answered, but returned data was unsupported by Funkwhale.</translate></p>
          </div>
          <div v-else-if="fetch.status === 'finished'" class="ui success message">
            <div class="header"><translate translate-context="Popup/*/Message.Title">Refresh successful</translate></div>
            <p><translate translate-context="Popup/*/Message.Content">Data was refreshed successfully from remote server.</translate></p>
          </div>
          <div v-else-if="fetch.status === 'errored'" class="ui error message">
            <div class="header"><translate translate-context="Popup/*/Message.Title">Refresh error</translate></div>
            <p><translate translate-context="Popup/*/Message.Content">An error occurred while trying to refresh data:</translate></p>
            <table class="ui very basic collapsing celled table">
              <tbody>
                <tr>
                  <td>
                    <translate translate-context="Popup/Import/Table.Label/Noun">Error type</translate>
                  </td>
                  <td>
                    {{ fetch.detail.error_code }}
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Popup/Import/Table.Label/Noun">Error detail</translate>
                  </td>
                  <td>
                    <translate
                      v-if="fetch.detail.error_code === 'http' && fetch.detail.status_code"
                      :translate-params="{status: fetch.detail.status_code}"
                      translate-context="*/*/Error">The remote server answered with HTTP %{ status }</translate>
                    <translate
                      v-else-if="['http', 'request'].indexOf(fetch.detail.error_code) > -1"
                      translate-context="*/*/Error">An HTTP error occurred while contacting the remote server</translate>
                    <translate
                      v-else-if="fetch.detail.error_code === 'timeout'"
                      translate-context="*/*/Error">The remote server didn't respond quickly enough</translate>
                    <translate
                      v-else-if="fetch.detail.error_code === 'connection'"
                      translate-context="*/*/Error">Impossible to connect to the remote server</translate>
                    <translate
                      v-else-if="['invalid_json', 'invalid_jsonld', 'missing_jsonld_type'].indexOf(fetch.detail.error_code) > -1"
                      translate-context="*/*/Error">The remote server returned invalid JSON or JSON-LD data</translate>
                    <translate v-else-if="fetch.detail.error_code === 'validation'" translate-context="*/*/Error">Data returned by the remote server had invalid or missing attributes</translate>
                    <translate v-else-if="fetch.detail.error_code === 'unhandled'" translate-context="*/*/Error">Unknown error</translate>
                    <translate v-else translate-context="*/*/Error">Unknown error</translate>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
        <div v-else-if="isCreatingFetch" class="ui active inverted dimmer">
          <div class="ui text loader">
            <translate translate-context="Popup/*/Loading.Title">Requesting a fetch…</translate>
          </div>
        </div>
        <div v-else-if="isWaitingFetch" class="ui active inverted dimmer">
          <div class="ui text loader">
            <translate translate-context="Popup/*/Loading.Title">Waiting for result…</translate>
          </div>
        </div>
        <div v-if="errors.length > 0" role="alert" class="ui negative message">
          <div class="header"><translate translate-context="Content/*/Error message.Title">Error while saving settings</translate></div>
          <ul class="list">
            <li v-for="error in errors">{{ error }}</li>
          </ul>
        </div>
        <div v-else-if="fetch && fetch.status === 'pending' && pollsCount >= maxPolls" role="alert" class="ui warning message">
          <div class="header"><translate translate-context="Popup/*/Message.Title">Refresh pending</translate></div>
          <p><translate translate-context="Popup/*/Message.Content">Refresh request wasn't proceed in time by our server. It will be processed later.</translate></p>
        </div>
      </div>
      <div class="actions">
        <div role="button" class="ui basic cancel button">
          <translate translate-context="*/*/Button.Label/Verb">Close</translate>
        </div>
        <div role="button" @click="showModal = false; $emit('refresh')" class="ui confirm green button" v-if="fetch && fetch.status === 'finished'">
          <translate translate-context="*/*/Button.Label/Verb">Close and reload page</translate>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
import axios from "axios"
import Modal from '@/components/semantic/Modal'

export default {
  props: ['url'],
  components: {
    Modal
  },
  data () {
    return {
      fetch: null,
      isCreatingFetch: false,
      errors: [],
      showModal: false,
      isWaitingFetch: false,
      maxPolls: 15,
      pollsCount: 0,
    }
  },
  methods: {
    createFetch () {
      let self = this
      this.fetch = null
      this.pollsCount = 0
      this.errors = []
      this.isCreatingFetch = true
      this.isWaitingFetch = false
      self.showModal = true
      axios.post(this.url).then((response) => {
        self.isCreatingFetch = false
        self.fetch = response.data
        self.pollFetch()
      }, (error) => {
        self.isCreatingFetch = false
        self.errors = error.backendErrors
      })
    },
    pollFetch () {
      this.isWaitingFetch = true
      this.pollsCount += 1
      let url = `federation/fetches/${this.fetch.id}/`
      let self = this
      self.showModal = true
      axios.get(url).then((response) => {
        self.isCreatingFetch = false
        self.fetch = response.data
        if (self.fetch.status === 'pending' && self.pollsCount < self.maxPolls) {
          setTimeout(() => {
            self.pollFetch()
          }, 1000)
        } else {
          self.isWaitingFetch = false
        }
      }, (error) => {
        self.errors = error.backendErrors
        self.isWaitingFetch = false
      })
    }
  }
}
</script>
