<template>
  <div class="main pusher"  v-title="labels.moderation">
    <nav class="ui secondary pointing menu" role="navigation" :aria-label="labels.secondaryMenu">
      <router-link
        class="ui item"
        :to="{name: 'manage.moderation.reports.list', query: {q: 'resolved:no'}}">
        <translate translate-context="*/Moderation/*/Noun">Reports</translate>
        <div
          v-if="$store.state.ui.notifications.pendingReviewReports > 0"
          :class="['ui', 'circular', 'mini', 'right floated', 'accent', 'label']">{{ $store.state.ui.notifications.pendingReviewReports }}</div>
      </router-link>
      <router-link
        class="ui item"
        :to="{name: 'manage.moderation.requests.list', query: {q: 'status:pending'}}">
        <translate translate-context="*/Moderation/*/Noun">User Requests</translate>
        <div
          v-if="$store.state.ui.notifications.pendingReviewRequests > 0"
          :class="['ui', 'circular', 'mini', 'right floated', 'accent', 'label']">{{ $store.state.ui.notifications.pendingReviewRequests }}</div>
      </router-link>
      <router-link
        class="ui item"
        :to="{name: 'manage.moderation.domains.list'}"><translate translate-context="*/Moderation/*/Noun">Domains</translate></router-link>
      <router-link
        class="ui item"
        :to="{name: 'manage.moderation.accounts.list'}"><translate translate-context="*/Moderation/Title">Accounts</translate></router-link>

    </nav>
    <router-view :allow-list-enabled="allowListEnabled" :key="$route.fullPath"></router-view>
  </div>
</template>

<script>
import _ from '@/lodash'
import axios from 'axios'

export default {
  data () {
    return {
      allowListEnabled: false
    }
  },
  created () {
    this.fetchNodeInfo()
  },
  methods: {
    fetchNodeInfo () {
      let self = this
      axios.get('instance/nodeinfo/2.0/').then(response => {
        self.allowListEnabled = _.get(response.data, 'metadata.allowList.enabled', false)
      })
    },
  },
  computed: {
    labels() {
      return {
        moderation: this.$pgettext('*/Moderation/*', "Moderation"),
        secondaryMenu: this.$pgettext('Menu/*/Hidden text', "Secondary menu")
      }
    }
  },
}
</script>
