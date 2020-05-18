var sinon = require('sinon')
import {expect} from 'chai'

import moxios from 'moxios'
import store from '@/store/auth'

import { testAction } from '../../utils'

describe('store/auth', () => {
  var sandbox

  beforeEach(function () {
    sandbox = sinon.createSandbox()
    moxios.install()
  })
  afterEach(function () {
    sandbox.restore()
    moxios.uninstall()
  })

  describe('mutations', () => {
    it('profile', () => {
      const state = {}
      store.mutations.profile(state, {})
      expect(state.profile).to.deep.equal({})
    })
    it('username', () => {
      const state = {}
      store.mutations.username(state, 'world')
      expect(state.username).to.equal('world')
    })
    it('authenticated true', () => {
      const state = {}
      store.mutations.authenticated(state, true)
      expect(state.authenticated).to.equal(true)
    })
    it('authenticated false', () => {
      const state = {
        username: 'dummy',
        token: 'dummy',
        profile: 'dummy',
        availablePermissions: 'dummy'
      }
      store.mutations.authenticated(state, false)
      expect(state.authenticated).to.equal(false)
      expect(state.username).to.equal(null)
      expect(state.token).to.equal(null)
      expect(state.profile).to.equal(null)
      expect(state.availablePermissions).to.deep.equal({})
    })
    it('token null', () => {
      const state = {}
      store.mutations.token(state, null)
      expect(state.token).to.equal(null)
    })
    it('token real', () => {
      const state = {}
      let token = 'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2p3dC1pZHAuZXhhbXBsZS5jb20iLCJzdWIiOiJtYWlsdG86bWlrZUBleGFtcGxlLmNvbSIsIm5iZiI6MTUxNTUzMzQyOSwiZXhwIjoxNTE1NTM3MDI5LCJpYXQiOjE1MTU1MzM0MjksImp0aSI6ImlkMTIzNDU2IiwidHlwIjoiaHR0cHM6Ly9leGFtcGxlLmNvbS9yZWdpc3RlciJ9.'
      store.mutations.token(state, token)
      expect(state.token).to.equal(token)
    })
    it('permissions', () => {
      const state = { availablePermissions: {} }
      store.mutations.permission(state, {key: 'admin', status: true})
      expect(state.availablePermissions).to.deep.equal({admin: true})
    })
  })
  describe('getters', () => {
    it('header', () => {
      const state = { oauth: {accessToken: 'helloworld' }}
      expect(store.getters['header'](state)).to.equal('Bearer helloworld')
    })
  })
  describe('actions', () => {
    it('logout', () => {
      testAction({
        action: store.actions.logout,
        params: {state: {}},
        expectedMutations: [
          { type: 'auth/reset', payload: null, options: {root: true} },
          { type: 'favorites/reset', payload: null, options: {root: true} },
          { type: 'player/reset', payload: null, options: {root: true} },
          { type: 'playlists/reset', payload: null, options: {root: true} },
          { type: 'queue/reset', payload: null, options: {root: true} },
          { type: 'radios/reset', payload: null, options: {root: true} }
        ]
      })
    })
    it('check jwt null', () => {
      testAction({
        action: store.actions.check,
        params: {state: {}},
        expectedMutations: [
          { type: 'authenticated', payload: false },
          { type: 'authenticated', payload: true },
        ],
        expectedActions: [
          { type: 'fetchProfile' },
        ]
      })
    })
    it('login success', () => {
      moxios.stubRequest('token/', {
        status: 200,
        response: {
          token: 'test'
        }
      })
      const credentials = {
        username: 'bob'
      }
      testAction({
        action: store.actions.login,
        payload: {credentials: credentials},
        expectedMutations: [
          { type: 'token', payload: 'test' }
        ],
        expectedActions: [
          { type: 'fetchProfile' }
        ]
      })
    })
    it('login error', () => {
      moxios.stubRequest('token/', {
        status: 500,
        response: {
          token: 'test'
        }
      })
      const credentials = {
        username: 'bob'
      }
      let spy = sandbox.spy()
      testAction({
        action: store.actions.login,
        payload: {credentials: credentials, onError: spy}
      }, () => {
        expect(spy.calledOnce).to.equal(true)
        done() // eslint-disable-line no-undef
      })
    })
    it('fetchProfile', () => {
      const profile = {
        username: 'bob',
        permissions: {
          admin: true
        }
      }
      moxios.stubRequest('users/users/me/', {
        status: 200,
        response: profile
      })
      testAction({
        action: store.actions.fetchProfile,
        expectedMutations: [
          { type: 'authenticated', payload: true },
          { type: 'profile', payload: profile },
          { type: 'username', payload: profile.username },
          { type: 'permission', payload: {key: 'admin', status: true} }
        ],
        expectedActions: [
          { type: 'favorites/fetch', payload: null, options: {root: true} },
          { type: 'playlists/fetchOwn', payload: null, options: {root: true} }
        ]
      })
    })
  })
})
