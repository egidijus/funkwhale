<template>
  <div class="ui card">
    <div class="content">
      <h4 class="header">
        <router-link :to="{name: 'library.detail', params: {id: library.uuid}}">
          {{ library.name }}
        </router-link>
        <div class="ui right floated dropdown" v-dropdown>
          <i class="ellipsis vertical large icon nomargin"></i>
          <div class="menu">
            <button
              v-for="obj in getReportableObjs({library, account: library.actor})"
              :key="obj.target.type + obj.target.id"
              class="item basic"
              @click.stop.prevent="$store.dispatch('moderation/report', obj.target)">
              <i class="share icon" /> {{ obj.label }}
            </button>
          </div>
        </div>
        <span
          v-if="library.privacy_level === 'me'"
          class="right floated"
          :data-tooltip="labels.tooltips.me">
          <i class="small lock icon"></i>
        </span>
        <span
          v-else-if="library.privacy_level === 'everyone'"
          class="right floated"
          :data-tooltip="labels.tooltips.everyone">
          <i class="small globe icon"></i>
        </span>
      </h4>
      <div class="meta">
        <span>
          <i class="small outline clock icon" />
          <human-date :date="library.creation_date" />
        </span>
      </div>
      <div class="description">
        {{ library.description }}
        <div class="ui hidden divider"></div>
      </div>
      <div class="meta">
        <i class="music icon"></i>
        <translate translate-context="*/*/*" :translate-params="{count: library.uploads_count}" :translate-n="library.uploads_count" translate-plural="%{ count } tracks">%{ count } track</translate>
      </div>
      <div v-if="displayScan && latestScan" class="meta">
        <template v-if="latestScan.status === 'pending'">
          <i class="hourglass icon"></i>
          <translate translate-context="Content/Library/Card.List item">Scan pending</translate>
        </template>
        <template v-if="latestScan.status === 'scanning'">
          <i class="loading spinner icon"></i>
          <translate translate-context="Content/Library/Card.List item" :translate-params="{progress: scanProgress}">Scanning… (%{ progress }%)</translate>
        </template>
        <template v-else-if="latestScan.status === 'errored'">
          <i class="dangerdownload icon"></i>
          <translate translate-context="Content/Library/Card.List item">Problem during scanning</translate>
        </template>
        <template v-else-if="latestScan.status === 'finished' && latestScan.errored_files === 0">
          <i class="success download icon"></i>
          <translate translate-context="Content/Library/Card.List item">Scanned</translate>
        </template>
        <template v-else-if="latestScan.status === 'finished' && latestScan.errored_files > 0">
          <i class="warning download icon"></i>
          <translate translate-context="Content/Library/Card.List item">Scanned with errors</translate>
        </template>
        <a href="" class="link right floated" @click.prevent="showScan = !showScan">
          <translate translate-context="Content/Library/Card.Button.Label/Noun">Details</translate>
          <i v-if="showScan" class="angle down icon" />
          <i v-else class="angle right icon" />
        </a>
        <div v-if="showScan">
          <template v-if="latestScan.modification_date">
            <translate translate-context="Content/Library/Card.List item/Noun">Last update:</translate><human-date :date="latestScan.modification_date" /><br />
          </template>
          <translate translate-context="Content/Library/Card.List item/Noun">Failed tracks:</translate> {{ latestScan.errored_files }}
        </div>
      </div>
      <div v-if="displayScan && canLaunchScan" class="clearfix">
        <a href="" class="right floated link" @click.prevent="launchScan">
          <translate translate-context="Content/Library/Card.Button.Label/Verb">Scan now</translate> <i class="paper plane icon" />
        </a>
      </div>
    </div>
    <div class="extra content">
      <actor-link style="color: var(--link-color)" :actor="library.actor" />
    </div>
    <div v-if="displayCopyFid" class="extra content">
      <div class="ui form">
        <div class="field">
          <label :for="library.fid"><translate translate-context="Content/Library/Title">Sharing link</translate></label>
          <copy-input :id="library.fid" :button-classes="'basic'" :value="library.fid" />
        </div>
      </div>
    </div>
    <div v-if="displayFollow || radioPlayable" :class="['ui', {two: displayFollow && radioPlayable}, 'bottom', 'attached', 'buttons']">
      <radio-button v-if="radioPlayable" :type="'library'" :object-id="library.uuid"></radio-button>
      <template v-if="displayFollow">
        <button
          v-if="!library.follow"
          @click="follow()"
          :class="['ui', 'success', {'loading': isLoadingFollow}, 'button']">
          <translate translate-context="Content/Library/Card.Button.Label/Verb">Follow</translate>
        </button>
        <template v-else-if="!library.follow.approved">
          <button
            class="ui disabled button"><i class="hourglass icon"></i>
            <translate translate-context="Content/Library/Card.Paragraph">Follow request pending approval</translate>
          </button>
          <button
            @click="unfollow"
            class="ui button">
            <translate translate-context="Content/Library/Card.Paragraph">Cancel follow request</translate>
          </button>
        </template>
        <template v-else-if="library.follow.approved">
          <dangerous-button
            :class="['ui', 'button']"
            :action="unfollow">
            <translate translate-context="*/Library/Button.Label/Verb">Unfollow</translate>
            <p slot="modal-header"><translate translate-context="Popup/Library/Title">Unfollow this library?</translate></p>
            <div slot="modal-content">
              <p><translate translate-context="Popup/Library/Paragraph">By unfollowing this library, you loose access to its content.</translate></p>
            </div>
            <div slot="modal-confirm"><translate translate-context="*/Library/Button.Label/Verb">Unfollow</translate></div>
          </dangerous-button>
        </template>
      </template>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
import ReportMixin from '@/components/mixins/Report'
import RadioButton from '@/components/radios/Button'
import jQuery from 'jquery'

export default {
  mixins: [ReportMixin],
  props: {
    library: {type: Object, required: true},
    displayFollow: {type: Boolean, default: true},
    displayScan: {type: Boolean, default: true},
    displayCopyFid: {type: Boolean, default: true},
  },
  components: {
    RadioButton
  },
  data () {
    return {
      isLoadingFollow: false,
      showScan: false,
      scanTimeout: null,
      latestScan: this.library.latest_scan,
    }
  },
  computed: {
    labels () {
      let me = this.$pgettext('Content/Library/Card.Help text', 'This library is private and your approval from its owner is needed to access its content')
      let everyone = this.$pgettext('Content/Library/Card.Help text', 'This library is public and you can access its content freely')

      return {
        tooltips: {
          me,
          everyone
        }
      }
    },
    scanProgress () {
      let scan = this.latestScan
      let progress = scan.processed_files * 100 / scan.total_files
      return Math.min(parseInt(progress), 100)
    },
    scanStatus () {
      if (this.latestScan) {
        return this.latestScan.status
      }
      return 'unknown'
    },
    canLaunchScan () {
      if (this.scanStatus === 'pending') {
        return false
      }
      if (this.scanStatus === 'scanning') {
        return false
      }
      return true
    },
    radioPlayable () {
      return (
        (this.library.actor.is_local || this.scanStatus === 'finished') &&
        (this.library.privacy_level === 'everyone' || (this.library.follow && this.library.follow.is_approved))
      )
    },
  },
  methods: {
    launchScan () {
      let self = this
      let successMsg = this.$pgettext('Content/Library/Message', 'Scan launched')
      let skippedMsg = this.$pgettext('Content/Library/Message', 'Scan skipped (previous scan is too recent)')
      axios.post(`federation/libraries/${this.library.uuid}/scan/`).then((response) => {
        let msg
        if (response.data.status == 'skipped') {
          msg = skippedMsg
        } else {
          self.latestScan = response.data.scan
          msg = successMsg
        }
        self.$store.commit('ui/addMessage', {
          content: msg,
          date: new Date()
        })
      })
    },
    follow () {
      let self = this
      this.isLoadingFollow = true
      axios.post('federation/follows/library/', {target: this.library.uuid}).then((response) => {
        self.library.follow = response.data
        self.isLoadingFollow = false
        self.$emit('followed')

      }, error => {
        self.isLoadingFollow = false
      })
    },
    unfollow () {
      let self = this
      this.isLoadingFollow = true
      axios.delete(`federation/follows/library/${this.library.follow.uuid}/`).then((response) => {
        self.$emit('deleted')
        self.library.follow = null
        self.isLoadingFollow = false
      }, error => {
        self.isLoadingFollow = false
      })
    },
    fetchScanStatus () {
      let self = this
      axios.get(`federation/follows/library/${this.library.follow.uuid}/`).then((response) => {
        self.latestScan = response.data.target.latest_scan
        if (self.scanStatus === 'pending' || self.scanStatus === 'scanning') {
          self.scanTimeout = setTimeout(self.fetchScanStatus(), 5000)
        } else {
          clearTimeout(self.scanTimeout)
        }
      })
    }
  },
  watch: {
    showScan (newValue, oldValue) {
      if (newValue) {
        if (this.scanStatus === 'pending' || this.scanStatus === 'scanning') {
          this.fetchScanStatus()
        }
      } else {
        if (this.scanTimeout) {
          clearTimeout(this.scanTimeout)
        }
      }
    }
  }
}
</script>
