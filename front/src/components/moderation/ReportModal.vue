<template>
  <modal @update:show="update" :show="$store.state.moderation.showReportModal">
    <h2 class="ui header" v-if="target">
      <translate translate-context="Popup/Moderation/Title/Verb">Do you want to report this object?</translate>
      <div class="ui sub header">
        {{ target.typeLabel }} - {{ target.label }}
      </div>
    </h2>
    <div class="scrolling content">
      <div class="description">
        <div v-if="errors.length > 0" role="alert" class="ui negative message">
          <div class="header"><translate translate-context="Popup/Moderation/Error message">Error while submitting report</translate></div>
          <ul class="list">
            <li v-for="error in errors">{{ error }}</li>
          </ul>
        </div>
      </div>
      <p>
        <translate translate-context="*/Moderation/Popup,Paragraph">Use this form to submit a report to our moderation team.</translate>
      </p>
      <form v-if="canSubmit" id="report-form" class="ui form" @submit.prevent="submit">
        <div class="fields">
          <report-category-dropdown
            class="ui required eight wide field"
            v-model="category"
            :required="true"
            :empty="true"
            :restrict-to="allowedCategories"
            :label="true"></report-category-dropdown>
          <div v-if="!$store.state.auth.authenticated" class="ui eight wide required field">
            <label for="report-submitter-email">
              <translate translate-context="Content/*/*/Noun">Email</translate>
            </label>
            <input type="email" v-model="submitterEmail" name="report-submitter-email" id="report-submitter-email" required>
            <p>
              <translate translate-context="*/*/Field,Help">We'll use this email if we need to contact you regarding this report.</translate>
            </p>
          </div>
        </div>
        <div class="ui field">
          <label for="report-summary">
            <translate translate-context="*/*/Field.Label/Noun">Message</translate>
          </label>
          <p>
            <translate translate-context="*/*/Field,Help">Use this field to provide additional context to the moderator that will handle your report.</translate>
          </p>
          <content-form field-id="report-summary" :rows="8" v-model="summary"></content-form>
        </div>
        <div class="ui field" v-if="!isLocal">
          <div class="ui checkbox">
            <input id="report-forward" v-model="forward" type="checkbox">
            <label for="report-forward">
              <strong>
                <translate :translate-params="{domain: targetDomain}" translate-context="*/*/Field.Label/Verb">Forward to %{ domain} </translate>
              </strong>
              <p>
                <translate translate-context="*/*/Field,Help">Forward an anonymized copy of your report to the server hosting this element.</translate>
              </p>
            </label>
          </div>
        </div>
        <div class="ui hidden divider"></div>
      </form>
      <div v-else-if="isLoadingReportTypes" class="ui inline active loader">

      </div>
      <div v-else role="alert" class="ui warning message">
        <div class="header">
          <translate translate-context="Popup/Moderation/Error message">Anonymous reports are disabled, please sign-in to submit a report.</translate>
        </div>
      </div>
    </div>
    <div class="actions">
      <div class="ui basic cancel button"><translate translate-context="*/*/Button.Label/Verb">Cancel</translate></div>
      <button
        v-if="canSubmit"
        :class="['ui', 'success', {loading: isLoading}, 'button']"
        type="submit" form="report-form">
        <translate translate-context="Popup/*/Button.Label">Submit report</translate>
      </button>
    </div>
  </modal>
</template>

<script>
import _ from '@/lodash'
import axios from 'axios'
import {mapState} from 'vuex'

import logger from '@/logging'

function urlDomain(data) {
  var    a      = document.createElement('a');
         a.href = data;
  return a.hostname;
}

export default {
  components: {
    ReportCategoryDropdown:  () => import(/* webpackChunkName: "reports" */ "@/components/moderation/ReportCategoryDropdown"),
    Modal:  () => import(/* webpackChunkName: "modal" */ "@/components/semantic/Modal"),
  },
  data () {
    return {
      formKey: String(new Date()),
      errors: [],
      isLoading: false,
      isLoadingReportTypes: false,
      summary: '',
      submitterEmail: '',
      category: null,
      reportTypes: [],
      forward: false,
    }
  },
  computed: {
    ...mapState({
      target: state => state.moderation.reportModalTarget,
    }),
    allowedCategories () {
      if (this.$store.state.auth.authenticated) {
        return []
      }
      return this.reportTypes.filter((t) => {
        return t.anonymous === true
      }).map((c) => {
        return c.type
      })

    },
    canSubmit () {
      if (this.$store.state.auth.authenticated) {
        return true
      }

      return this.allowedCategories.length > 0
    },
    targetDomain () {
      if (!this.target._obj) {
        return
      }
      let fid = this.target._obj.fid
      if (this.target.type === 'channel' && this.target._obj.actor ) {
        fid = this.target._obj.actor.fid
      }
      if (!fid) {
        return this.$store.getters['instance/domain']
      }
      return urlDomain(fid)
    },
    isLocal () {
      return this.$store.getters['instance/domain'] === this.targetDomain
    }
  },
  methods: {
    update (v) {
      this.$store.commit('moderation/showReportModal', v)
      this.errors = []
    },
    submit () {
      let self = this
      self.isLoading = true
      let payload = {
        target: {...this.target, _obj: null},
        summary: this.summary,
        type: this.category,
        forward: this.forward,
      }
      if (!this.$store.state.auth.authenticated) {
        payload.submitter_email = this.submitterEmail
      }
      return axios.post('moderation/reports/', payload).then(response => {
        self.update(false)
        self.isLoading = false
        let msg = this.$pgettext('*/Moderation/Message', 'Report successfully submitted, thank you')
        self.$store.commit('moderation/contentFilter', response.data)
        self.$store.commit('ui/addMessage', {
          content: msg,
          date: new Date()
        })
        self.summary = ''
        self.category = ''
      }, error => {
        self.errors = error.backendErrors
        self.isLoading = false
      })
    }
  },
  watch: {
    '$store.state.moderation.showReportModal': function (v) {
      if (!v || this.$store.state.auth.authenticated) {
        return
      }

      let self = this
      self.isLoadingReportTypes = true
      axios.get('instance/nodeinfo/2.0/').then(response => {
        self.isLoadingReportTypes = false
        self.reportTypes = response.data.metadata.reportTypes || []
      }, error => {
        self.isLoadingReportTypes = false
      })
    }
  }
}
</script>
