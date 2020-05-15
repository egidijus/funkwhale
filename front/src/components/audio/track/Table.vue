<template>
  <div class="table-wrapper component-track-table">
    <inline-search-bar v-model="query" v-if="search" @search="additionalTracks = []; loadMore()"></inline-search-bar>
    <slot v-if="!isLoading && allTracks.length === 0" name="empty-state">
      <empty-state @refresh="fetchData" :refresh="true"></empty-state>
    </slot>
    <table v-else :class="['ui', 'compact', 'very', 'basic', {loading: isLoading}, 'unstackable', 'table']">
      <thead>
        <tr>
          <th></th>
          <th></th>
          <th colspan="6"><translate translate-context="*/*/*/Noun">Title</translate></th>
          <th colspan="4"><translate translate-context="*/*/*/Noun">Artist</translate></th>
          <th colspan="4"><translate translate-context="*/*/*">Album</translate></th>
          <th colspan="4"><translate translate-context="Content/*/*">Duration</translate></th>
          <th colspan="2" v-if="displayActions"></th>
        </tr>
      </thead>
      <tbody>
        <track-row
          :playable="playable"
          :display-position="displayPosition"
          :display-actions="displayActions"
          :track="track"
          :artist="artist"
          :key="index + '-' + track.id"
          v-for="(track, index) in allTracks"></track-row>
      </tbody>
    </table>
    <button :class="['ui', {loading: isLoading}, 'button']" v-if="loadMoreUrl" @click="loadMore(loadMoreUrl)" :disabled="isLoading">
      <translate translate-context="Content/*/Button.Label">Load more…</translate>
    </button>
  </div>
</template>

<script>
import axios from 'axios'

import TrackRow from '@/components/audio/track/Row'
import Modal from '@/components/semantic/Modal'

export default {
  props: {
    tracks: {type: Array, required: false},
    playable: {type: Boolean, required: false, default: false},
    search: {type: Boolean, required: false, default: false},
    nextUrl: {type: String, required: false, default: null},
    artist: {type: Object, required: false},
    filters: {type: Object, required: false, default: () => { return {}}},
    displayPosition: {type: Boolean, default: false},
    displayActions: {type: Boolean, default: true},
  },
  components: {
    Modal,
    TrackRow
  },
  created () {
    if (!this.tracks) {
      this.loadMore('tracks/')
    }
  },
  data () {
    return {
      loadMoreUrl: this.nextUrl,
      isLoading: false,
      additionalTracks: [],
      query: '',
    }
  },
  computed: {
    allTracks () {
      return (this.tracks || []).concat(this.additionalTracks)
    }
  },
  methods: {
    loadMore (url) {
      url = url || 'tracks/'
      let self = this
      let params = {q: this.query, ...this.filters}
      self.isLoading = true
      axios.get(url, {params}).then((response) => {
        self.additionalTracks = self.additionalTracks.concat(response.data.results)
        self.loadMoreUrl = response.data.next
        self.isLoading = false
      }, (error) => {
        self.isLoading = false

      })
    }
  }
}
</script>
