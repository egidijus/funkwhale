import axios from 'axios'
import logger from '@/logging'
import time from '@/utils/time'

export default {
  namespaced: true,
  state: {
    maxConsecutiveErrors: 5,
    errorCount: 0,
    playing: false,
    isLoadingAudio: false,
    volume: 0.5,
    tempVolume: 0.5,
    duration: 0,
    currentTime: 0,
    errored: false,
    bufferProgress: 0,
    looping: 0 // 0 -> no, 1 -> on  track, 2 -> on queue
  },
  mutations: {
    reset (state) {
      state.errorCount = 0
      state.playing = false
    },
    volume (state, value) {
      value = parseFloat(value)
      value = Math.min(value, 1)
      value = Math.max(value, 0)
      state.volume = value
    },
    tempVolume (state, value) {
      value = parseFloat(value)
      value = Math.min(value, 1)
      value = Math.max(value, 0)
      state.tempVolume = value
    },
    incrementVolume (state, value) {
      value = parseFloat(state.volume + value)
      value = Math.min(value, 1)
      value = Math.max(value, 0)
      state.volume = value
    },
    incrementErrorCount (state) {
      state.errorCount += 1
    },
    resetErrorCount (state) {
      state.errorCount = 0
    },
    duration (state, value) {
      state.duration = value
    },
    errored (state, value) {
      state.errored = value
    },
    currentTime (state, value) {
      state.currentTime = value
    },
    looping (state, value) {
      state.looping = value
    },
    playing (state, value) {
      state.playing = value
    },
    bufferProgress (state, value) {
      state.bufferProgress = value
    },
    toggleLooping (state) {
      if (state.looping > 1) {
        state.looping = 0
      } else {
        state.looping += 1
      }
    },
    isLoadingAudio (state, value) {
      state.isLoadingAudio = value
    }
  },
  getters: {
    durationFormatted: state => {
      let duration = parseInt(state.duration)
      if (duration % 1 !== 0) {
        return time.parse(0)
      }
      duration = Math.round(state.duration)
      return time.parse(duration)
    },
    currentTimeFormatted: state => {
      return time.parse(Math.round(state.currentTime))
    },
    progress: state => {
      return Math.round(state.currentTime / state.duration * 100)
    }
  },
  actions: {
    incrementVolume ({commit, state}, value) {
      commit('volume', state.volume + value)
    },
    stop ({commit}) {
      commit('errored', false)
      commit('resetErrorCount')
    },
    togglePlay ({commit, state, dispatch}) {
      commit('playing', !state.playing)
      if (state.errored && state.errorCount < state.maxConsecutiveErrors) {
        setTimeout(() => {
          if (state.playing) {
            dispatch('queue/next', null, {root: true})
          }
        }, 3000)
      }
    },
    toggleMute({commit, state}) {
      if (state.volume > 0) {
        commit('tempVolume', state.volume)
        commit('volume', 0)
      }
      else {
        commit('volume', state.tempVolume)
      }
    },
    trackListened ({commit, rootState}, track) {
      if (!rootState.auth.authenticated) {
        return
      }
      return axios.post('history/listenings/', {'track': track.id}).then((response) => {}, (response) => {
        logger.default.error('Could not record track in history')
      })
    },
    nowPlaying ({commit, rootState}, trackData) {
      if (!rootState.auth.authenticated) {
        return
      }
      return axios.post('history/listenings/now/', {'track': trackData.id}).then((response) => {}, (response) => {
        logger.default.error('Could not set track as now playing')
      })
    },
    trackEnded ({dispatch, rootState}, track) {
      dispatch('trackListened', track)
      let queueState = rootState.queue
      if (queueState.currentIndex === queueState.tracks.length - 1) {
        // we've reached last track of queue, trigger a reload
        // from radio if any
        dispatch('radios/populateQueue', null, {root: true})
      }
      dispatch('queue/next', null, {root: true})
    },
    trackErrored ({commit, dispatch, state}) {
      commit('errored', true)
      commit('incrementErrorCount')
      if (state.errorCount < state.maxConsecutiveErrors) {
        setTimeout(() => {
          if (state.playing) {
            dispatch('queue/next', null, {root: true})
          }
        }, 3000)
      }
    },
    updateProgress ({commit}, t) {
      commit('currentTime', t)
    },
    mute({commit, state}) {
      commit('tempVolume', state.volume)
      commit('volume', 0)
    },
    unmute({commit, state}) {
      commit('volume', state.tempVolume)
    }
  }
}
