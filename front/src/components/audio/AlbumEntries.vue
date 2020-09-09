<template>
  <div class="album-entries">
    <div :class="[{active: currentTrack && isPlaying && track.id === currentTrack.id}, 'album-entry']" v-for="track in tracks" :key="track.id">
      <div class="actions">
        <play-button class="basic circular icon" :button-classes="['circular inverted vibrant icon button']" :discrete="true" :icon-only="true" :track="track"></play-button>
      </div>
      <div class="position">{{ prettyPosition(track.position) }}</div>
      <div class="content ellipsis">
        <router-link :to="{name: 'library.tracks.detail', params: {id: track.id}}" class="discrete link">
          <strong>{{ track.title }}</strong><br>
        </router-link>
      </div>
      <div class="meta">
        <template v-if="$store.state.auth.authenticated && $store.getters['favorites/isFavorite'](track.id)">
         <track-favorite-icon class="tiny" :track="track"></track-favorite-icon>
        </template>
        <human-duration v-if="track.uploads[0] && track.uploads[0].duration" :duration="track.uploads[0].duration"></human-duration>
      </div>
      <div class="actions">
        <play-button class="play-button basic icon" :dropdown-only="true" :is-playable="track.is_playable" :dropdown-icon-classes="['ellipsis', 'vertical', 'large really discrete']" :track="track"></play-button>      
      </div>
    </div>
  </div>
</template>

<script>
import _ from '@/lodash'
import axios from 'axios'
import ChannelEntryCard from '@/components/audio/ChannelEntryCard'
import PlayButton from '@/components/audio/PlayButton'
import TrackFavoriteIcon from '@/components/favorites/TrackFavoriteIcon'
import { mapGetters } from "vuex"


export default {
  props: {
    tracks: Array,
  },
  components: {
    PlayButton,
    TrackFavoriteIcon
  },
  computed: {
    ...mapGetters({
      currentTrack: "queue/currentTrack",
    }),

    isPlaying () {
      return this.$store.state.player.playing
    },
  },
  methods: {
    prettyPosition (position, size) {
      var s = String(position);
      while (s.length < (size || 2)) {s = "0" + s;}
      return s;
    }
  }
}
</script>
