import Vue from 'vue'
import axios from 'axios'
import logger from '@/logging'
import router from '@/router'
import lodash from '@/lodash'

function getDefaultScopedTokens () {
  return {
    listen: null,
  }
}
export default {
  namespaced: true,
  state: {
    authenticated: false,
    username: '',
    fullUsername: '',
    availablePermissions: {
      settings: false,
      library: false,
      moderation: false
    },
    profile: null,
    token: '',
    scopedTokens: getDefaultScopedTokens()
  },
  getters: {
    header: state => {
      if (state.token) {
        return 'JWT ' + state.token
      }
    }
  },
  mutations: {
    reset (state) {
      state.authenticated = false
      state.profile = null
      state.username = ''
      state.fullUsername = ''
      state.token = ''
      state.scopedTokens = getDefaultScopedTokens()
      state.availablePermissions = {
        federation: false,
        settings: false,
        library: false,
        upload: false
      }
    },
    profile: (state, value) => {
      state.profile = value
    },
    authenticated: (state, value) => {
      state.authenticated = value
      if (value === false) {
        state.username = null
        state.fullUsername = null
        state.token = null
        state.profile = null
        state.scopedTokens = getDefaultScopedTokens()
        state.availablePermissions = {}
      }
    },
    username: (state, value) => {
      state.username = value
    },
    fullUsername: (state, value) => {
      state.fullUsername = value
    },
    avatar: (state, value) => {
      if (state.profile) {
        state.profile.avatar = value
      }
    },
    token: (state, value) => {
      state.token = value
    },
    scopedTokens: (state, value) => {
      state.scopedTokens = {...value}
    },
    permission: (state, {key, status}) => {
      state.availablePermissions[key] = status
    },
    profilePartialUpdate: (state, payload) => {
      lodash.keys(payload).forEach((k) => {
        Vue.set(state.profile, k, payload[k])
      })
    }
  },
  actions: {
    // Send a request to the login URL and save the returned JWT
    login ({commit, dispatch}, {next, credentials, onError}) {
      return axios.post('token/', credentials).then(response => {
        logger.default.info('Successfully logged in as', credentials.username)
        commit('token', response.data.token)
        dispatch('fetchProfile').then(() => {
          // Redirect to a specified route
          router.push(next)
        })
      }, response => {
        logger.default.error('Error while logging in', response.data)
        onError(response)
      })
    },
    logout ({commit}) {
      let modules = [
        'auth',
        'favorites',
        'player',
        'playlists',
        'queue',
        'radios'
      ]
      modules.forEach(m => {
        commit(`${m}/reset`, null, {root: true})
      })
      logger.default.info('Log out, goodbye!')
      router.push({name: 'index'})
    },
    check ({commit, dispatch, state}) {
      logger.default.info('Checking authentication…')
      var jwt = state.token
      if (jwt) {
        commit('token', jwt)
        dispatch('fetchProfile')
        dispatch('refreshToken')
      } else {
        logger.default.info('Anonymous user')
        commit('authenticated', false)
      }
    },
    fetchProfile ({commit, dispatch, state}) {

      return new Promise((resolve, reject) => {
        axios.get('users/users/me/').then((response) => {
          logger.default.info('Successfully fetched user profile')
          dispatch('updateProfile', response.data).then(() => {
            resolve(response.data)
          })
          dispatch('ui/fetchUnreadNotifications', null, { root: true })
          if (response.data.permissions.library) {
            dispatch('ui/fetchPendingReviewEdits', null, { root: true })
          }
          if (response.data.permissions.moderation) {
            dispatch('ui/fetchPendingReviewReports', null, { root: true })
            dispatch('ui/fetchPendingReviewRequests', null, { root: true })
          }
          dispatch('favorites/fetch', null, { root: true })
          dispatch('channels/fetchSubscriptions', null, { root: true })
          dispatch('libraries/fetchFollows', null, { root: true })
          dispatch('moderation/fetchContentFilters', null, { root: true })
          dispatch('playlists/fetchOwn', null, { root: true })
        }, (response) => {
          logger.default.info('Error while fetching user profile')
          reject()
        })
      })
    },
    updateProfile({ commit }, data) {
      return new Promise((resolve, reject) => {
        commit("authenticated", true)
        commit("profile", data)
        commit("username", data.username)
        commit("fullUsername", data.full_username)
        if (data.tokens) {
          commit("scopedTokens", data.tokens)
        }
        Object.keys(data.permissions).forEach(function(key) {
          // this makes it easier to check for permissions in templates
          commit("permission", {
            key,
            status: data.permissions[String(key)]
          })
        })
        resolve()
      })
    },
    refreshToken ({commit, dispatch, state}) {
      return axios.post('token/refresh/', {token: state.token}).then(response => {
        logger.default.info('Refreshed auth token')
        commit('token', response.data.token)
      }, response => {
        logger.default.error('Error while refreshing token', response.data)
      })
    }
  }
}
