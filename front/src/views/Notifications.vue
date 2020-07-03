<template>
  <main class="main pusher page-notifications" v-title="labels.title">
    <section class="ui vertical aligned stripe segment">
      <div class="ui container">
        <div class="ui container" v-if="additionalNotifications">
          <h1 class="ui header"><translate translate-context="Content/Notifications/Title">Your messages</translate></h1>
          <div class="ui two column stackable grid">
            <div class="column" v-if="showInstanceSupportMessage">
              <div class="ui attached info message">
                <h4 class="header">
                  <translate translate-context="Content/Notifications/Header">Support this Funkwhale pod</translate>
                </h4>
                <div v-html="markdown.makeHtml($store.state.instance.settings.instance.support_message.value)"></div>
              </div>
              <div class="ui bottom attached segment">
                <form @submit.prevent="setDisplayDate('instance_support_message_display_date', instanceSupportMessageDelay)" class="ui inline form">
                  <div class="inline field">
                    <label>
                      <translate translate-context="Content/Notifications/Label">Remind me in:</translate>
                    </label>
                    <select v-model="instanceSupportMessageDelay">
                      <option :value="30"><translate translate-context="*/*/*">30 days</translate></option>
                      <option :value="60"><translate translate-context="*/*/*">60 days</translate></option>
                      <option :value="90"><translate translate-context="*/*/*">90 days</translate></option>
                      <option :value="null"><translate translate-context="*/*/*">Never</translate></option>
                    </select>
                    <button type="submit" class="ui right floated basic button">
                      <translate translate-context="Content/Notifications/Button.Label">Got it!</translate>
                    </button>
                  </div>
                </form>
              </div>
            </div>
            <div class="column" v-if="showFunkwhaleSupportMessage">
              <div class="ui info attached message">
                <h4 class="header">
                  <translate translate-context="Content/Notifications/Header">Do you like Funkwhale?</translate>
                </h4>
                <p>
                  <translate translate-context="Content/Notifications/Paragraph">We noticed you've been here for a while. If Funkwhale is useful to you, we could use your help to make it even better!</translate>
                </p>
                <a href="https://funkwhale.audio/support-us" _target="blank" rel="noopener" class="ui primary inverted button">
                  <translate translate-context="Content/Notifications/Button.Label/Verb">Donate</translate>
                </a>
                <a href="https://contribute.funkwhale.audio" _target="blank" rel="noopener" class="ui secondary inverted button">
                  <translate translate-context="Content/Notifications/Button.Label/Verb">Discover other ways to help</translate>
                </a>
              </div>
              <div class="ui bottom attached segment">
                <form @submit.prevent="setDisplayDate('funkwhale_support_message_display_date', funkwhaleSupportMessageDelay)" class="ui inline form">
                  <div class="inline field">
                    <label>
                      <translate translate-context="Content/Notifications/Label">Remind me in:</translate>
                    </label>
                    <select v-model="funkwhaleSupportMessageDelay">
                      <option :value="30"><translate translate-context="*/*/*">30 days</translate></option>
                      <option :value="60"><translate translate-context="*/*/*">60 days</translate></option>
                      <option :value="90"><translate translate-context="*/*/*">90 days</translate></option>
                      <option :value="null"><translate translate-context="*/*/*">Never</translate></option>
                    </select>
                    <button type="submit" class="ui right floated basic button">
                      <translate translate-context="Content/Notifications/Button.Label">Got it!</translate>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
        <h1 class="ui header"><translate translate-context="Content/Notifications/Title">Your notifications</translate></h1>
        <div class="ui toggle checkbox">
          <input v-model="filters.is_read" type="checkbox">
          <label><translate translate-context="Content/Notifications/Form.Label/Verb">Show read notifications</translate></label>
        </div>
        <div
          v-if="filters.is_read === false && notifications.count > 0"
          @click="markAllAsRead"
          class="ui basic labeled icon right floated button">
          <i class="ui check icon" />
          <translate translate-context="Content/Notifications/Button.Label/Verb">Mark all as read</translate>
        </div>
        <div class="ui hidden divider" />

        <div v-if="isLoading" :class="['ui', {'active': isLoading}, 'inverted', 'dimmer']">
          <div class="ui text loader"><translate translate-context="Content/Notifications/Paragraph">Loading notifications…</translate></div>
        </div>

        <table v-else-if="notifications.count > 0" class="ui table">
          <tbody>
            <notification-row :item="item" v-for="item in notifications.results" :key="item.id" />
          </tbody>
        </table>
        <p v-else-if="additionalNotifications === 0">
          <translate translate-context="Content/Notifications/Paragraph">No notification to show.</translate>
        </p>
      </div>
    </section>
  </main>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import axios from "axios"
import logger from "@/logging"
import showdown from 'showdown'
import moment from 'moment'

import NotificationRow from "@/components/notifications/NotificationRow"

export default {
  data() {
    return {
      isLoading: false,
      markdown: new showdown.Converter(),
      notifications: {count: 0, results: []},
      instanceSupportMessageDelay: 60,
      funkwhaleSupportMessageDelay: 60,
      filters: {
        is_read: false
      }
    }
  },
  components: {
    NotificationRow
  },
  created() {
    this.fetch(this.filters)
    this.$store.commit("ui/addWebsocketEventHandler", {
      eventName: "inbox.item_added",
      id: "notificationPage",
      handler: this.handleNewNotification
    })
  },
  destroyed() {
    this.$store.commit("ui/removeWebsocketEventHandler", {
      eventName: "inbox.item_added",
      id: "notificationPage"
    })
  },
  computed: {
    ...mapState({
      events: state => state.instance.events
    }),
    ...mapGetters({
      additionalNotifications: 'ui/additionalNotifications',
      showInstanceSupportMessage: 'ui/showInstanceSupportMessage',
      showFunkwhaleSupportMessage: 'ui/showFunkwhaleSupportMessage',
    }),
    labels() {
      return {
        title: this.$pgettext('*/Notifications/*', "Notifications")
      }
    }
  },
  methods: {
    handleNewNotification (event) {
      this.notifications.count += 1
      this.notifications.results.unshift(event.item)
    },
    setDisplayDate (field, days) {
      let payload = {}
      let newDisplayDate
      if (days) {
        newDisplayDate = moment().add({days})
      } else {
        newDisplayDate = null
      }
      payload[field] = newDisplayDate
      let self = this
      axios.patch(`users/users/${this.$store.state.auth.username}/`, payload).then((response) => {
        self.$store.commit('auth/profilePartialUpdate', response.data)
      })
    },
    fetch(params) {
      this.isLoading = true
      let self = this
      axios.get("federation/inbox/", { params: params }).then(response => {
        self.isLoading = false
        self.notifications = response.data
      })
    },
    markAllAsRead() {
      let self = this
      let before = this.notifications.results[0].id
      let payload = {
        action: "read",
        objects: "all",
        filters: {
          is_read: false,
          before
        }
      }
      axios.post("federation/inbox/action/", payload).then(response => {
        self.$store.commit("ui/notifications", { type: "inbox", count: 0 })
        self.notifications.results.forEach(n => {
          n.is_read = true
        })
      })
    }
  },
  watch: {
    "filters.is_read"() {
      this.fetch(this.filters)
    }
  }
}
</script>
