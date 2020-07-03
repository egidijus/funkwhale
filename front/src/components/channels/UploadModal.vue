<template>
  <modal class="small" @update:show="update" :show="$store.state.channels.showUploadModal">
    <h4 class="header">
      <translate key="1" v-if="step === 1" translate-context="Popup/Channels/Title/Verb">Publish audio</translate>
      <translate key="2" v-else-if="step === 2" translate-context="Popup/Channels/Title">Files to upload</translate>
      <translate key="3" v-else-if="step === 3" translate-context="Popup/Channels/Title">Upload details</translate>
      <translate key="4" v-else-if="step === 4" translate-context="Popup/Channels/Title">Processing uploads</translate>
    </h4>
    <div class="scrolling content">
      <channel-upload-form
        ref="uploadForm"
        @step="step = $event"
        @loading="isLoading = $event"
        @published="$store.commit('channels/publish', $event)"
        @status="statusData = $event"
        @submittable="submittable = $event"
        :channel="$store.state.channels.uploadModalConfig.channel"></channel-upload-form>
    </div>
    <div class="actions">
      <div class="left floated text left align">
        <template v-if="statusData && step >= 2">
          {{ statusInfo.join(' · ') }}
        </template>
        <div class="ui very small hidden divider"></div>
        <template v-if="statusData && statusData.quotaStatus">
          <translate translate-context="Content/Library/Paragraph">Remaining storage space:</translate>
          {{ (statusData.quotaStatus.remaining * 1000 * 1000) - statusData.uploadedSize | humanSize }}
        </template>
      </div>
      <div class="ui hidden clearing divider mobile-only"></div>
      <button class="ui basic cancel button" v-if="step === 1"><translate translate-context="*/*/Button.Label/Verb">Cancel</translate></button>
      <button class="ui basic button" v-else-if="step < 3" @click.stop.prevent="$refs.uploadForm.step -= 1"><translate translate-context="*/*/Button.Label/Verb">Previous step</translate></button>
      <button class="ui basic button" v-else-if="step === 3" @click.stop.prevent="$refs.uploadForm.step -= 1"><translate translate-context="*/*/Button.Label/Verb">Update</translate></button>
      <button v-if="step === 1" class="ui primary button" @click.stop.prevent="$refs.uploadForm.step += 1">
        <translate translate-context="*/*/Button.Label">Next step</translate>
      </button>
      <div class="ui primary buttons" v-if="step === 2">
        <button
          :class="['ui', 'primary button', {loading: isLoading}]"
          type="submit"
          :disabled="!statusData || !statusData.canSubmit"
          @click.prevent.stop="$refs.uploadForm.publish">
          <translate translate-context="*/Channels/Button.Label">Publish</translate>
        </button>
        <button class="ui floating dropdown icon button" ref="dropdown" v-dropdown :disabled="!statusData || !statusData.canSubmit">
          <i class="dropdown icon"></i>
          <div class="menu">
            <div
              role="button"
              @click="update(false)"
              class="basic item">
              <translate translate-context="Content/*/Button.Label/Verb">Finish later</translate>
            </div>
          </div>
        </button>
      </div>
      <button class="ui basic cancel button" @click="update(false)" v-if="step === 4"><translate translate-context="*/*/Button.Label/Verb">Close</translate></button>
    </div>
  </modal>
</template>

<script>
import Modal from '@/components/semantic/Modal'
import ChannelUploadForm from '@/components/channels/UploadForm'
import {humanSize} from '@/filters'

export default {
  components: {
    Modal,
    ChannelUploadForm
  },
  data () {
    return {
      step: 1,
      isLoading: false,
      submittable: true,
      statusData: null,
    }
  },
  methods: {
    update (v) {
      this.$store.commit('channels/showUploadModal', {show: v})
    },
  },
  computed: {
    labels () {
      return {}
    },
    statusInfo () {
      if (!this.statusData) {
        return []
      }
      let info = []
      if (this.statusData.totalSize) {
        info.push(humanSize(this.statusData.totalSize))
      }
      if (this.statusData.totalFiles) {
        let msg = this.$npgettext('*/*/*', '%{ count } file', '%{ count } files', this.statusData.totalFiles)
        info.push(
          this.$gettextInterpolate(msg, {count: this.statusData.totalFiles}),
        )
      }
      if (this.statusData.progress) {
        info.push(`${this.statusData.progress}%`)
      }
      if (this.statusData.speed) {
        info.push(`${humanSize(this.statusData.speed)}/s`)
      }
      return info

    }
  },
  watch: {
    '$store.state.route.path' () {
      this.$store.commit('channels/showUploadModal', {show: false})
    },
  }
}
</script>
