<template>
  <tr :class="[{'disabled-row': item.is_read}]">
    <td>
      <actor-link class="user" :actor="item.activity.actor" />
    </td>
    <td>
      <router-link tag="span" class="link" v-if="notificationData.detailUrl" :to="notificationData.detailUrl" v-html="notificationData.message">

      </router-link>
      <template v-else v-html="notificationData.message"></template>
      <template v-if="notificationData.acceptFollow">&nbsp;
        <button @click="handleAction(notificationData.acceptFollow.handler)" :class="['ui', 'basic', 'tiny', notificationData.acceptFollow.buttonClass || '', 'button']">
          <i v-if="notificationData.acceptFollow.icon" :class="[notificationData.acceptFollow.icon, 'icon']" />
          {{ notificationData.acceptFollow.label }}
        </button>
        <button @click="handleAction(notificationData.rejectFollow.handler)" :class="['ui', 'basic', 'tiny', notificationData.rejectFollow.buttonClass || '', 'button']">
          <i v-if="notificationData.rejectFollow.icon" :class="[notificationData.rejectFollow.icon, 'icon']" />
          {{ notificationData.rejectFollow.label }}
        </button>
      </template>
    </td>
    <td><human-date :date="item.activity.creation_date" /></td>
    <td class="read collapsing">
      <span @click="markRead(false)" role="button" v-if="item.is_read" :title="labels.markUnread">
        <i class="redo icon" />
      </span>
      <span @click="markRead(true)" role="button" v-else :title="labels.markRead">
        <i class="check icon" />
      </span>
    </td>
  </tr>
</template>
<script>
import axios from 'axios'

export default {
  props: ['item'],
  computed: {
    message () {
      return 'plop'
    },
    labels () {
      let libraryFollowMessage = this.$pgettext('Content/Notifications/Paragraph', '%{ username } followed your library "%{ library }"')
      let libraryAcceptFollowMessage = this.$pgettext('Content/Notifications/Paragraph', '%{ username } accepted your follow on library "%{ library }"')
      let libraryRejectMessage = this.$pgettext('Content/Notifications/Paragraph', 'You rejected %{ username }&#39;s request to follow "%{ library }"')
      let libraryPendingFollowMessage = this.$pgettext('Content/Notifications/Paragraph', '%{ username } wants to follow your library "%{ library }"')
      return {
        libraryFollowMessage,
        libraryAcceptFollowMessage,
        libraryRejectMessage,
        libraryPendingFollowMessage,
        markRead: this.$pgettext('Content/Notifications/Button.Tooltip/Verb', 'Mark as read'),
        markUnread: this.$pgettext('Content/Notifications/Button.Tooltip/Verb', 'Mark as unread'),

      }
    },
    username () {
      return this.item.activity.actor.preferred_username
    },
    notificationData () {
      let self = this
      let a = this.item.activity
      if (a.type === 'Follow') {
        if (a.object && a.object.type === 'music.Library') {
          let acceptFollow = null
          let rejectFollow = null
          let message = null
          if (a.related_object.approved === null) {
            message = this.labels.libraryPendingFollowMessage
            acceptFollow = {
              buttonClass: 'success',
              icon: 'check',
              label: this.$pgettext('Content/*/Button.Label/Verb', 'Approve'),
              handler: () => { self.approveLibraryFollow(a.related_object) }
            },
            rejectFollow = {
              buttonClass: 'danger',
              icon: 'x',
              label: this.$pgettext('Content/*/Button.Label/Verb', 'Reject'),
              handler: () => { self.rejectLibraryFollow(a.related_object) }
            }
          } else if (a.related_object.approved) {
            message = this.labels.libraryFollowMessage
          } else {
            message = this.labels.libraryRejectMessage
          }
          return {
            acceptFollow,
            rejectFollow,
            detailUrl: {name: 'content.libraries.detail', params: {id: a.object.uuid}},
            message: this.$gettextInterpolate(
              message,
              {username: this.username, library: a.object.name}
            )
          }
        }
      }
      if (a.type === 'Accept') {
        if (a.object && a.object.type === 'federation.LibraryFollow') {
          return {
            detailUrl: {name: 'content.remote.index'},
            message: this.$gettextInterpolate(
              this.labels.libraryAcceptFollowMessage,
              {username: this.username, library: a.related_object.name}
            )
          }
        }
      }
      return {}
    }
  },
  methods: {
    handleAction (handler) {
      // call handler then mark notification as read
      handler()
      this.markRead(true)
    },
    approveLibraryFollow (follow) {
      let self = this
      let action = 'accept'
      axios.post(`federation/follows/library/${follow.uuid}/${action}/`).then((response) => {
        follow.isLoading = false
        follow.approved = true
      })
    },
    rejectLibraryFollow (follow) {
      let self = this
      let action = 'reject'
      axios.post(`federation/follows/library/${follow.uuid}/${action}/`).then((response) => {
        follow.isLoading = false
        follow.approved = false
      })
    },
    markRead (value) {
      let self = this
      let action = 'accept'
      axios.patch(`federation/inbox/${this.item.id}/`, {is_read: value}).then((response) => {
        self.item.is_read = value
        if (value) {
          self.$store.commit('ui/incrementNotifications', {type: 'inbox', count: -1})
        } else {
          self.$store.commit('ui/incrementNotifications', {type: 'inbox', count: 1})
        }
      })
    }
  }
}
</script>
