import axios from 'axios'
import moment from 'moment'

export default {
  namespaced: true,
  state: {
    currentLanguage: 'en_US',
    selectedLanguage: false,
    queueFocused: null,
    momentLocale: 'en',
    lastDate: new Date(),
    maxMessages: 100,
    messageDisplayDuration: 5 * 1000,
    supportedExtensions: ["flac", "ogg", "mp3", "opus", "aac", "m4a"],
    messages: [],
    theme: 'light',
    window: {
      height: 0,
      width: 0,
    },
    notifications: {
      inbox: 0,
      pendingReviewEdits: 0,
      pendingReviewReports: 0,
      pendingReviewRequests: 0,
    },
    websocketEventsHandlers: {
      'inbox.item_added': {},
      'import.status_updated': {},
      'mutation.created': {},
      'mutation.updated': {},
      'report.created': {},
      'user_request.created': {},
      'Listen': {},
    },
    pageTitle: null,
    routePreferences: {
      "library.albums.browse": {
        paginateBy: 25,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.artists.browse": {
        paginateBy: 30,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.radios.browse": {
        paginateBy: 12,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.playlists.browse": {
        paginateBy: 25,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.albums.me": {
        paginateBy: 25,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.artists.me": {
        paginateBy: 30,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.radios.me": {
        paginateBy: 12,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.playlists.me": {
        paginateBy: 25,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "content.libraries.files": {
        paginateBy: 50,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.detail.upload": {
        paginateBy: 50,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.detail.edit": {
        paginateBy: 50,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "library.detail": {
        paginateBy: 50,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "favorites": {
        paginateBy: 50,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "manage.moderation.requests.list": {
        paginateBy: 25,
        orderingDirection: "-",
        ordering: "creation_date",
      },
      "manage.moderation.reports.list": {
        paginateBy: 25,
        orderingDirection: "-",
        ordering: "creation_date",
      },
    },
    serviceWorker: {
      refreshing: false,
      registration: null,
      updateAvailable: false,
    }
  },
  getters: {
    showInstanceSupportMessage: (state, getters, rootState) => {
      if (!rootState.auth.profile) {
        return false
      }
      if (!rootState.instance.settings.instance.support_message.value) {
        return false
      }
      let displayDate = rootState.auth.profile.instance_support_message_display_date
      if (!displayDate) {
        return false
      }
      return moment(displayDate) < moment(state.lastDate)
    },
    showFunkwhaleSupportMessage: (state, getters, rootState) => {
      if (!rootState.auth.profile) {
        return false
      }
      if (!rootState.instance.settings.instance.funkwhale_support_message_enabled.value) {
        return false
      }
      let displayDate = rootState.auth.profile.funkwhale_support_message_display_date
      if (!displayDate) {
        return false
      }
      return moment(displayDate) < moment(state.lastDate)
    },
    additionalNotifications: (state, getters) => {
      let count = 0
      if (getters.showInstanceSupportMessage) {
        count += 1
      }
      if (getters.showFunkwhaleSupportMessage) {
        count += 1
      }
      return count
    },

    windowSize: (state, getters) => {
      // IMPORTANT: if you modify these breakpoints, also modify the values in
      // style/vendor/_media.scss
      let width = state.window.width
      let breakpoints = [
        {name: 'widedesktop', width: 1200},
        {name: 'desktop', width: 1024},
        {name: 'tablet', width: 768},
        {name: 'phone', width: 320},
      ]
      for (let index = 0; index < breakpoints.length; index++) {
        const element = breakpoints[index];
        if (width >= element.width) {
          return element.name
        }
      }
      return 'phone'

    },
    layoutVersion: (state, getters) => {
      if (['tablet', 'phone'].indexOf(getters.windowSize) > -1) {
        return 'small'
      } else {
        return 'large'
      }
    }
  },
  mutations: {
    addWebsocketEventHandler: (state, {eventName, id, handler}) => {
      state.websocketEventsHandlers[eventName][id] = handler
    },
    removeWebsocketEventHandler: (state, {eventName, id}) => {
      delete state.websocketEventsHandlers[eventName][id]
    },
    currentLanguage: (state, value) => {
      state.currentLanguage = value
      state.selectedLanguage = true
    },
    momentLocale: (state, value) => {
      state.momentLocale = value
      moment.locale(value)
    },
    computeLastDate: (state) => {
      state.lastDate = new Date()
    },
    queueFocused: (state, value) => {
      state.queueFocused = value
    },

    theme: (state, value) => {
      state.theme = value
    },
    addMessage (state, message) {
      let finalMessage = {
        displayTime: state.messageDisplayDuration,
        key: String(new Date()),
        ...message,
      }
      let key = finalMessage.key
      state.messages = state.messages.filter((m) => {
        return m.key != key
      })
      state.messages.push(finalMessage)
      if (state.messages.length > state.maxMessages) {
        state.messages.shift()
      }
    },
    removeMessage (state, key) {
      state.messages = state.messages.filter((m) => {
        return m.key != key
      })
    },
    notifications (state, {type, count}) {
      state.notifications[type] = count
    },
    incrementNotifications (state, {type, count, value}) {
      if (value != undefined) {
          state.notifications[type] = Math.max(0, value)
      } else {
        state.notifications[type] = Math.max(0, state.notifications[type] + count)
      }
    },
    pageTitle: (state, value) => {
      state.pageTitle = value
    },
    paginateBy: (state, {route, value}) => {
      state.routePreferences[route].paginateBy = value
    },
    ordering: (state, {route, value}) => {
      state.routePreferences[route].ordering = value
    },
    orderingDirection: (state, {route, value}) => {
      state.routePreferences[route].orderingDirection = value
    },

    serviceWorker: (state, value) => {
      state.serviceWorker = {...state.serviceWorker, ...value}
    },
    window: (state, value) => {
      state.window = value
    }
  },
  actions: {
    fetchUnreadNotifications ({commit}, payload) {
      axios.get('federation/inbox/', {params: {is_read: false, page_size: 1}}).then((response) => {
        commit('notifications', {type: 'inbox', count: response.data.count})
      })
    },
    fetchPendingReviewEdits ({commit, rootState}, payload) {
      axios.get('mutations/', {params: {is_approved: 'null', page_size: 1}}).then((response) => {
        commit('notifications', {type: 'pendingReviewEdits', count: response.data.count})
      })
    },
    fetchPendingReviewReports ({commit, rootState}, payload) {
      axios.get('manage/moderation/reports/', {params: {is_handled: 'false', page_size: 1}}).then((response) => {
        commit('notifications', {type: 'pendingReviewReports', count: response.data.count})
      })
    },
    fetchPendingReviewRequests ({commit, rootState}, payload) {
      axios.get('manage/moderation/requests/', {params: {status: 'pending', page_size: 1}}).then((response) => {
        commit('notifications', {type: 'pendingReviewRequests', count: response.data.count})
      })
    },

    async currentLanguage ({state, commit, rootState}, value) {
      commit("currentLanguage", value)
      if (rootState.auth.authenticated) {
        await axios.post("users/settings", {"language": value})
      }
    },

    async theme ({state, commit, rootState}, value) {
      commit("theme", value)
      if (rootState.auth.authenticated) {
        await axios.post("users/settings", {"theme": value})
      }
    },

    async initSettings ({commit}, settings) {
      settings = settings || {}
      if (settings.language) {
        commit("currentLanguage", settings.language)
      }
      if (settings.theme) {
        commit("theme", settings.theme)
      }
    },
    websocketEvent ({state}, event) {
      let handlers = state.websocketEventsHandlers[event.type]
      console.log('Dispatching websocket event', event, handlers)
      if (!handlers) {
        return
      }
      let names = Object.keys(handlers)
      names.forEach((k) => {
        let handler = handlers[k]
        handler(event)
      })
    }
  }
}
