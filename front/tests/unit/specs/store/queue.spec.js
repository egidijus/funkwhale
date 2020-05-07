var sinon = require('sinon')
import {expect} from 'chai'

import _ from '@/lodash'

import store from '@/store/queue'
import { testAction } from '../../utils'

describe('store/queue', () => {
  var sandbox

  beforeEach(function () {
    // Create a sandbox for the test
    sandbox = sinon.createSandbox()
  })

  afterEach(function () {
    // Restore all the things made through the sandbox
    sandbox.restore()
  })
  describe('mutations', () => {
    it('currentIndex', () => {
      const state = {}
      store.mutations.currentIndex(state, 2)
      expect(state.currentIndex).to.equal(2)
    })
    it('ended', () => {
      const state = {}
      store.mutations.ended(state, false)
      expect(state.ended).to.equal(false)
    })
    it('tracks', () => {
      const state = {}
      store.mutations.tracks(state, [1, 2])
      expect(state.tracks).to.deep.equal([1, 2])
    })
    it('splice', () => {
      const state = {tracks: [1, 2, 3]}
      store.mutations.splice(state, {start: 1, size: 2})
      expect(state.tracks).to.deep.equal([1])
    })
    it('insert', () => {
      const state = {tracks: [1, 3]}
      store.mutations.insert(state, {track: 2, index: 1})
      expect(state.tracks).to.deep.equal([1, 2, 3])
    })
    it('reorder before', () => {
      const state = {currentIndex: 3}
      store.mutations.reorder(state, {oldIndex: 2, newIndex: 1})
      expect(state.currentIndex).to.equal(3)
    })
    it('reorder from after to before', () => {
      const state = {currentIndex: 3}
      store.mutations.reorder(state, {oldIndex: 4, newIndex: 1})
      expect(state.currentIndex).to.equal(4)
    })
    it('reorder after', () => {
      const state = {currentIndex: 3}
      store.mutations.reorder(state, {oldIndex: 4, newIndex: 5})
      expect(state.currentIndex).to.equal(3)
    })
    it('reorder before to after', () => {
      const state = {currentIndex: 3}
      store.mutations.reorder(state, {oldIndex: 1, newIndex: 5})
      expect(state.currentIndex).to.equal(2)
    })
    it('reorder current', () => {
      const state = {currentIndex: 3}
      store.mutations.reorder(state, {oldIndex: 3, newIndex: 1})
      expect(state.currentIndex).to.equal(1)
    })
  })
  describe('getters', () => {
    it('currentTrack', () => {
      const state = { tracks: [1, 2, 3], currentIndex: 2 }
      expect(store.getters['currentTrack'](state)).to.equal(3)
    })
    it('hasNext true', () => {
      const state = { tracks: [1, 2, 3], currentIndex: 1 }
      expect(store.getters['hasNext'](state)).to.equal(true)
    })
    it('hasNext false', () => {
      const state = { tracks: [1, 2, 3], currentIndex: 2 }
      expect(store.getters['hasNext'](state)).to.equal(false)
    })
  })
  describe('actions', () => {
    it('append at end', () => {
      testAction({
        action: store.actions.append,
        payload: {track: 4},
        params: {state: {tracks: [1, 2, 3]}},
        expectedMutations: [
          { type: 'insert', payload: {track: 4, index: 3} }
        ]
      })
    })
    it('append at index', () => {
      testAction({
        action: store.actions.append,
        payload: {track: 2, index: 1},
        params: {state: {tracks: [1, 3]}},
        expectedMutations: [
          { type: 'insert', payload: {track: 2, index: 1} }
        ]
      })
    })
    it('appendMany', () => {
      const tracks = [{title: 1}, {title: 2}]
      testAction({
        action: store.actions.appendMany,
        payload: {tracks: tracks},
        params: {state: {tracks: []}},
        expectedActions: [
          { type: 'append', payload: {track: tracks[0], index: 0} },
          { type: 'append', payload: {track: tracks[1], index: 1} },
        ]
      })
    })
    it('appendMany at index', () => {
      const tracks = [{title: 1}, {title: 2}]
      testAction({
        action: store.actions.appendMany,
        payload: {tracks: tracks, index: 1},
        params: {state: {tracks: [1, 2]}},
        expectedActions: [
          { type: 'append', payload: {track: tracks[0], index: 1} },
          { type: 'append', payload: {track: tracks[1], index: 2} },
        ]
      })
    })
    it('cleanTrack after current', () => {
      testAction({
        action: store.actions.cleanTrack,
        payload: 3,
        params: {state: {currentIndex: 2, tracks: [1, 2, 3, 4, 5]}},
        expectedMutations: [
          { type: 'splice', payload: {start: 3, size: 1} }
        ]
      })
    })
    it('cleanTrack before current', () => {
      testAction({
        action: store.actions.cleanTrack,
        payload: 1,
        params: {state: {currentIndex: 2, tracks: []}},
        expectedMutations: [
          { type: 'splice', payload: {start: 1, size: 1} },
          { type: 'currentIndex', payload: 1 }
        ]
      })
    })
    it('cleanTrack current', () => {
      testAction({
        action: store.actions.cleanTrack,
        payload: 2,
        params: {state: {currentIndex: 2, tracks: []}},
        expectedMutations: [
          { type: 'splice', payload: {start: 2, size: 1} },
          { type: 'currentIndex', payload: 2 }
        ],
        expectedActions: [
          { type: 'player/stop', payload: null, options: {root: true} }
        ]
      })
    })
    it('previous when at beginning', () => {
      testAction({
        action: store.actions.previous,
        params: {state: {currentIndex: 0}},
        expectedActions: [
          { type: 'currentIndex', payload: 0 }
        ]
      })
    })
    it('previous after less than 3 seconds of playback', () => {
      testAction({
        action: store.actions.previous,
        params: {state: {currentIndex: 1}, rootState: {player: {currentTime: 1}}},
        expectedActions: [
          { type: 'currentIndex', payload: 0 }
        ]
      })
    })
    it('previous after more than 3 seconds of playback', () => {
      testAction({
        action: store.actions.previous,
        params: {state: {currentIndex: 1}, rootState: {player: {currentTime: 3}}},
        expectedActions: [
          { type: 'currentIndex', payload: 1 }
        ]
      })
    })
    it('next on last track when looping on queue', () => {
      testAction({
        action: store.actions.next,
        params: {state: {tracks: [1, 2], currentIndex: 1}, rootState: {player: {looping: 2}}},
        expectedActions: [
          { type: 'currentIndex', payload: 0 }
        ]
      })
    })
    it('next track when last track', () => {
      testAction({
        action: store.actions.next,
        params: {state: {tracks: [1, 2], currentIndex: 1}, rootState: {player: {looping: 0}}},
        expectedMutations: [
          { type: 'ended', payload: true }
        ]
      })
    })
    it('next track when not last track', () => {
      testAction({
        action: store.actions.next,
        params: {state: {tracks: [1, 2], currentIndex: 0}, rootState: {player: {looping: 0}}},
        expectedActions: [
          { type: 'currentIndex', payload: 1 }
        ]
      })
    })
    it('currentIndex', () => {
      testAction({
        action: store.actions.currentIndex,
        payload: 1,
        params: {state: {tracks: [1, 2], currentIndex: 0}, rootState: {radios: {running: false}}},
        expectedMutations: [
          { type: 'ended', payload: false },
          { type: 'player/currentTime', payload: 0, options: {root: true} },
          { type: 'currentIndex', payload: 1 }
        ]
      })
    })
    it('currentIndex with radio and many tracks remaining', () => {
      testAction({
        action: store.actions.currentIndex,
        payload: 1,
        params: {state: {tracks: [1, 2, 3, 4], currentIndex: 0}, rootState: {radios: {running: true}}},
        expectedMutations: [
          { type: 'ended', payload: false },
          { type: 'player/currentTime', payload: 0, options: {root: true} },
          { type: 'currentIndex', payload: 1 }
        ]
      })
    })
    it('currentIndex with radio and less than two tracks remaining', () => {
      testAction({
        action: store.actions.currentIndex,
        payload: 1,
        params: {state: {tracks: [1, 2, 3], currentIndex: 0}, rootState: {radios: {running: true}}},
        expectedMutations: [
          { type: 'ended', payload: false },
          { type: 'player/currentTime', payload: 0, options: {root: true} },
          { type: 'currentIndex', payload: 1 }
        ],
        expectedActions: [
          { type: 'radios/populateQueue', payload: null, options: {root: true} }
        ]
      })
    })
    it('clean', () => {
      testAction({
        action: store.actions.clean,
        expectedMutations: [
          { type: 'tracks', payload: [] },
          { type: 'ended', payload: true }
        ],
        expectedActions: [
          { type: 'radios/stop', payload: null, options: {root: true} },
          { type: 'player/stop', payload: null, options: {root: true} },
          { type: 'currentIndex', payload: -1 }
        ]
      })
    })
    it('shuffle', () => {
      let _shuffle = sandbox.stub(_, 'shuffle')
      let tracks = ['a', 'b', 'c', 'd', 'e']
      let shuffledTracks = ['e', 'd', 'c']
      _shuffle.returns(shuffledTracks)
      testAction({
        action: store.actions.shuffle,
        params: {state: {currentIndex: 1, tracks: tracks}},
        expectedMutations: [
          { type: 'tracks', payload: [] }
        ],
        expectedActions: [
          { type: 'appendMany', payload: {tracks: ['a', 'b'].concat(shuffledTracks)} }
        ]
      })
    })
  })
})
