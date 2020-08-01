<template>
  <div>
    <h3 v-if="!!this.$slots.title" class="ui header">
      <slot name="title"></slot>
    </h3>
    <div v-if="isLoading" class="ui inverted active dimmer">
      <div class="ui loader"></div>
    </div>
    <div v-if="playlistsExist" class="ui cards app-cards">
      <playlist-card v-for="playlist in objects" :key="playlist.id" :playlist="playlist"></playlist-card>
    </div>
    <div v-else class="ui placeholder segment">
      <div class="ui icon header">
        <i class="list icon"></i>
        <translate translate-context="Content/Home/Placeholder">
          No playlists have been created yet
        </translate>
      </div>
      <button
        v-if="$store.state.auth.authenticated"
        @click="$store.commit('playlists/chooseTrack', null)"
        class="ui success icon labeled button"
        >
        <i class="list icon"></i>
        <translate translate-context="Content/Home/CreatePlaylist">
          Create Playlist
        </translate>
      </button>
    </div>
    <template v-if="nextPage">
      <div class="ui hidden divider"></div>
      <button v-if="nextPage" @click="fetchData(nextPage)" :class="['ui', 'basic', 'button']">
        <translate translate-context="*/*/Button,Label">Show more</translate>
      </button>
    </template>
  </div>
</template>

<script>
import _ from '@/lodash'
import axios from 'axios'
import PlaylistCard from '@/components/playlists/Card'

export default {
  props: {
    filters: {type: Object, required: true},
    url: {type: String, required: true}
  },
  components: {
    PlaylistCard
  },
  data () {
    return {
      objects: [],
      limit: this.filters.limit || 3,
      isLoading: false,
      errors: null,
      previousPage: null,
      nextPage: null
    }
  },
  created () {
    this.fetchData(this.url)
  },
  computed: {
    playlistsExist: function () {
      return this.objects.length > 0
    }
  },
  methods: {
    fetchData (url) {
      if (!url) {
        return
      }
      this.isLoading = true
      let self = this
      let params = _.clone(this.filters)
      params.page_size = this.limit
      params.offset = this.offset
      axios.get(url, {params: params}).then((response) => {
        self.previousPage = response.data.previous
        self.nextPage = response.data.next
        self.isLoading = false
        self.objects = [...self.objects, ...response.data.results]
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    updateOffset (increment) {
      if (increment) {
        this.offset += this.limit
      } else {
        this.offset = Math.max(this.offset - this.limit, 0)
      }
    }
  },
  watch: {
    offset () {
      this.fetchData()
    },
    "$store.state.moderation.lastUpdate": function () {
      this.fetchData(this.url)
    }
  }
}
</script>
