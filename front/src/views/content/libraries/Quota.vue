<template>
  <div class="ui segment">
    <h3 class="ui header"><translate translate-context="Content/Library/Title">Current usage</translate></h3>
    <div v-if="isLoading" :class="['ui', {'active': isLoading}, 'inverted', 'dimmer']">
      <div class="ui text loader"><translate translate-context="Content/Library/Paragraph">Loading usage data…</translate></div>
    </div>
    <div :class="['ui', {'success': progress < 60}, {'warning': progress >= 60 && progress < 96}, {'error': progress >= 95}, 'progress']" data-percent=progress>
      <div class="bar" :style="{width: `${progress}%`}">
        <div class="progress">{{ progress }}%</div>
      </div>
      <div class="label" v-if="quotaStatus">
        <translate translate-context="Content/Library/Paragraph" :translate-params="{max: humanSize(quotaStatus.max * 1000 * 1000), current: humanSize(quotaStatus.current * 1000 * 1000)}">%{ current } used on %{ max } allowed</translate>
      </div>
    </div>
    <div class="ui hidden divider"></div>
    <div v-if="quotaStatus" class="ui stackable three column grid">
      <div v-if="quotaStatus.pending > 0" class="column">
        <div class="ui tiny warning statistic">
          <div class="value">
            {{ humanSize(quotaStatus.pending * 1000 * 1000) }}
          </div>
          <div class="label">
            <translate translate-context="Content/Library/Label">Pending files</translate>
          </div>
        </div>
        <div>
          <router-link
            class="ui basic primary tiny button"
            :to="{name: 'content.libraries.files', query: {q: compileTokens([{field: 'status', value: 'pending'}])}}">
            <translate translate-context="Content/Library/Link/Verb">View files</translate>
          </router-link>

          <dangerous-button
            class="ui basic tiny button"
            :action="purgePendingFiles">
            <translate translate-context="*/*/*/Verb">Purge</translate>
            <p slot="modal-header"><translate translate-context="Popup/Library/Title">Purge pending files?</translate></p>
            <p slot="modal-content"><translate translate-context="Popup/Library/Paragraph">Removes uploaded but yet to be processed tracks completely, adding the corresponding data to your quota.</translate></p>
            <div slot="modal-confirm"><translate translate-context="*/*/*/Verb">Purge</translate></div>
          </dangerous-button>
        </div>
      </div>
      <div v-if="quotaStatus.skipped > 0" class="column">
        <div class="ui tiny statistic">
          <div class="value">
            {{ humanSize(quotaStatus.skipped * 1000 * 1000) }}
          </div>
          <div class="label">
            <translate translate-context="Content/Library/Label">Skipped files</translate>
          </div>
        </div>
        <div>
          <router-link
            class="ui basic primary tiny button"
            :to="{name: 'content.libraries.files', query: {q: compileTokens([{field: 'status', value: 'skipped'}])}}">
            <translate translate-context="Content/Library/Link/Verb">View files</translate>
          </router-link>
          <dangerous-button
            class="ui basic tiny button"
            :action="purgeSkippedFiles">
            <translate translate-context="*/*/*/Verb">Purge</translate>
            <p slot="modal-header"><translate translate-context="Popup/Library/Title">Purge skipped files?</translate></p>
            <p slot="modal-content"><translate translate-context="Popup/Library/Paragraph">Removes uploaded tracks skipped during the import processes completely, adding the corresponding data to your quota.</translate></p>
            <div slot="modal-confirm"><translate translate-context="*/*/*/Verb">Purge</translate></div>
          </dangerous-button>
        </div>
      </div>
      <div v-if="quotaStatus.errored > 0" class="column">
        <div class="ui tiny danger statistic">
          <div class="value">
            {{ humanSize(quotaStatus.errored * 1000 * 1000) }}
          </div>
          <div class="label">
            <translate translate-context="Content/Library/Label">Errored files</translate>
          </div>
        </div>
        <div>
          <router-link
            class="ui basic primary tiny button"
            :to="{name: 'content.libraries.files', query: {q: compileTokens([{field: 'status', value: 'errored'}])}}">
            <translate translate-context="Content/Library/Link/Verb">View files</translate>
          </router-link>
          <dangerous-button
            class="ui basic tiny button"
            :action="purgeErroredFiles">
            <translate translate-context="*/*/*/Verb">Purge</translate>
            <p slot="modal-header"><translate translate-context="Popup/Library/Title">Purge errored files?</translate></p>
            <p slot="modal-content"><translate translate-context="Popup/Library/Paragraph">Removes uploaded tracks that could not be processed by the server completely, adding the corresponding data to your quota.</translate></p>
            <div slot="modal-confirm"><translate translate-context="*/*/*/Verb">Purge</translate></div>
          </dangerous-button>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
import {humanSize} from '@/filters'
import {compileTokens} from '@/search'

export default {
  data () {
    return {
      quotaStatus: null,
      isLoading: false,
      humanSize,
      compileTokens
    }
  },
  created () {
    this.fetch()
  },
  methods: {
    fetch () {
      let self = this
      self.isLoading = true
      axios.get('users/users/me/').then((response) => {
        self.quotaStatus = response.data.quota_status
        self.isLoading = false
      })
    },
    purge (status) {
      let self = this
      let payload = {
        action: 'delete',
        objects: 'all',
        filters: {
          import_status: status
        }
      }
      axios.post('uploads/action/', payload).then((response) => {
        self.fetch()
      })
    },
    purgeSkippedFiles () {
      this.purge('skipped')
    },
    purgePendingFiles () {
      this.purge('pending')
    },
    purgeErroredFiles () {
      this.purge('errored')
    },
  },
  computed: {
    progress () {
      if (!this.quotaStatus) {
        return 0
      }
      return Math.min(parseInt(this.quotaStatus.current * 100 / this.quotaStatus.max), 100)
    }
  }
}
</script>
