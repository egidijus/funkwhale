import axios from 'axios'
import logger from '@/logging'

import {getClientOnlyRadio} from '@/radios'

export default {
  namespaced: true,
  state: {
    current: null,
    running: false
  },
  getters: {
    types: state => {
      return {
        'actor-content': {
          name: 'Your content',
          description: "Picks from your own libraries"
        },
        random: {
          name: 'Random',
          description: "Totally random picks, maybe you'll discover new things?"
        },
        favorites: {
          name: 'Favorites',
          description: 'Play your favorites tunes in a never-ending happiness loop.'
        },
        'less-listened': {
          name: 'Less listened',
          description: "Listen to tracks you usually don't. It's time to restore some balance."
        }
      }
    }
  },
  mutations: {
    reset (state) {
      state.running = false
      state.current = false
    },
    current: (state, value) => {
      state.current = value
    },
    running: (state, value) => {
      state.running = value
    }
  },
  actions: {
    start ({commit, dispatch}, {type, objectId, customRadioId, clientOnly}) {
      var params = {
        radio_type: type,
        related_object_id: objectId,
        custom_radio: customRadioId,
      }
      if (clientOnly) {
        commit('current', {type, objectId, customRadioId, clientOnly})
        commit('running', true)
        dispatch('populateQueue', true)
        return
      }
      return axios.post('radios/sessions/', params).then((response) => {
        logger.default.info('Successfully started radio ', type)
        commit('current', {type, objectId, session: response.data.id, customRadioId})
        commit('running', true)
        dispatch('populateQueue', true)
      }, (response) => {
        logger.default.error('Error while starting radio', type)
      })
    },
    stop ({commit, state}) {
      if (state.current && state.current.clientOnly) {
        getClientOnlyRadio(state.current).stop()
      }
      commit('current', null)
      commit('running', false)
    },
    populateQueue ({rootState, state, dispatch}, playNow) {
      if (!state.running) {
        return
      }
      if (rootState.player.errorCount >= rootState.player.maxConsecutiveErrors - 1) {
        return
      }
      var params = {
        session: state.current.session
      }
      if (state.current.clientOnly) {
        return getClientOnlyRadio(state.current).populateQueue({current: state.current, dispatch, state, rootState, playNow})
      }
      return axios.post('radios/tracks/', params).then((response) => {
        logger.default.info('Adding track to queue from radio')
        let append = dispatch('queue/append', {track: response.data.track}, {root: true})
        if (playNow) {
          append.then(() => {
            dispatch('queue/last', null, {root: true})
          })
        }
      }, (response) => {
        logger.default.error('Error while adding track to queue from radio')
      })
    }
  }

}
