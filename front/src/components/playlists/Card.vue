<template>
  <div class="ui app-card card">
    <div
      @click="$router.push({name: 'library.playlists.detail', params: {id: playlist.id }})"
      :class="['ui', 'head-image', 'squares']">
      <img v-lazy="url" v-for="(url, idx) in images" :key="idx" />
      <play-button :icon-only="true" :is-playable="playlist.is_playable" :button-classes="['ui', 'circular', 'large', 'vibrant', 'icon', 'button']" :playlist="playlist"></play-button>
    </div>
    <div class="content">
      <strong>
        <router-link class="discrete link" :title="playlist.name" :to="{name: 'library.playlists.detail', params: {id: playlist.id }}">
          {{ playlist.name }}
        </router-link>
      </strong>
      <div class="description">
        <user-link :user="playlist.user" :avatar="false" class="left floated" />
      </div>
    </div>
    <div class="extra content">
      <translate translate-context="*/*/*" :translate-params="{count: playlist.tracks_count}" :translate-n="playlist.tracks_count" translate-plural="%{ count } tracks">%{ count } track</translate>
      <play-button class="right floated basic icon" :dropdown-only="true" :is-playable="playlist.is_playable" :dropdown-icon-classes="['ellipsis', 'horizontal', 'large really discrete']" :playlist="playlist"></play-button>
    </div>
  </div>
</template>

<script>
import PlayButton from '@/components/audio/PlayButton'

export default {
  props: ['playlist'],
  components: {
    PlayButton
  },
  computed: {
    images () {
      let self = this
      let urls = this.playlist.album_covers.map((url) => {
        return self.$store.getters['instance/absoluteUrl'](url)
      }).slice(0, 4)
      while (urls.length < 4) {
        urls.push(
          require('../../assets/audio/default-cover.png')
        )
      }
      return urls
    }
  }
}
</script>
