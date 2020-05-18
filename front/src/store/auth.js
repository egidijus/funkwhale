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

function asForm (obj) {
  let data = new FormData()
  Object.entries(obj).forEach((e) => {
    data.set(e[0], e[1])
  })
  return data
}


let baseUrl = `${window.location.protocol}//${window.location.hostname}`
if (window.location.port) {
  baseUrl = `${baseUrl}:${window.location.port}`
}
function getDefaultOauth () {
  return {
    clientId: null,
    clientSecret: null,
    accessToken: null,
    refreshToken: null,
  }
}
const NEEDED_SCOPES = [
  "read",
  "write",
].join(' ')
async function createOauthApp(domain) {
  const payload = {
    name: `Funkwhale web client at ${window.location.hostname}`,
    website: baseUrl,
    scopes: NEEDED_SCOPES,
    redirect_uris: `${baseUrl}/auth/callback`
  }
  return (await axios.post('oauth/apps/', payload)).data
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
    oauth: getDefaultOauth(),
    scopedTokens: getDefaultScopedTokens()
  },
  getters: {
    header: state => {
      if (state.oauth.accessToken) {
        return 'Bearer ' + state.oauth.accessToken
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
      state.oauth = getDefaultOauth()
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
    },
    oauthApp: (state, payload) => {
      state.oauth.clientId = payload.client_id
      state.oauth.clientSecret = payload.client_secret
    },
    oauthToken: (state, payload) => {
      state.oauth.accessToken = payload.access_token
      state.oauth.refreshToken = payload.refresh_token
    }
  },
  actions: {
    // Send a request to the login URL and save the returned JWT
    login ({commit, dispatch}, {next, credentials, onError}) {
      var form = new FormData();
      Object.keys(credentials).forEach((k) => {
        form.set(k, credentials[k])
      })
      return axios.post('users/login', form).then(response => {
        logger.default.info('Successfully logged in as', credentials.username)
        // commit('token', response.data.token)
        dispatch('fetchProfile').then(() => {
          // Redirect to a specified route
          router.push(next)
        })
      }, response => {
        logger.default.error('Error while logging in', response.data)
        onError(response)
      })
    },
    async logout ({state, commit}) {
      try {
        await axios.post('users/logout')
      } catch {
        console.log('Error while logging out, probably logged in via oauth')
      }
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
    async check ({commit, dispatch, state}) {
      logger.default.info('Checking authentication…')
      commit('authenticated', false)
      let profile = await dispatch('fetchProfile')
      if (profile) {
        commit('authenticated', true)
      } else {
        logger.default.info('Anonymous user')
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
    async oauthLogin({ state, rootState, commit, getters }, next) {
      let app = await createOauthApp(getters["appDomain"])
      commit("oauthApp", app)
      const redirectUri = encodeURIComponent(`${baseUrl}/auth/callback`)
      let params = `response_type=code&scope=${encodeURIComponent(NEEDED_SCOPES)}&redirect_uri=${redirectUri}&state=${next}&client_id=${state.oauth.clientId}`
      const authorizeUrl = `${rootState.instance.instanceUrl}authorize?${params}`
      console.log('Redirecting user...', authorizeUrl)
      window.location = authorizeUrl
    },
    async handleOauthCallback({ state, commit, dispatch }, authorizationCode) {
      console.log('Fetching token...')
      const payload = {
        client_id: state.oauth.clientId,
        client_secret: state.oauth.clientSecret,
        grant_type: "authorization_code",
        code: authorizationCode,
        redirect_uri: `${baseUrl}/auth/callback`
      }
      const response = await axios.post(
        'oauth/token/',
        asForm(payload),
        {headers: {'Content-Type': 'multipart/form-data'}}
      )
      commit("oauthToken", response.data)
      await dispatch('fetchProfile')
    },
    async refreshOauthToken({ state, commit }, authorizationCode) {
      const payload = {
        client_id: state.oauth.clientId,
        client_secret: state.oauth.clientSecret,
        grant_type: "refresh_token",
        refresh_token: state.oauth.refreshToken,
      }
      let response = await axios.post(
        `oauth/token/`,
        asForm(payload),
        {headers: {'Content-Type': 'multipart/form-data'}}
      )
      commit('oauthToken', response.data)
    },
  }
}
