<template>
  <tr>
    <td>
      <play-button :class="['basic', {vibrant: currentTrack && isPlaying && track.id === currentTrack.id}, 'icon']" :discrete="true" :is-playable="playable" :track="track"></play-button>
    </td>
    <td>
      <img class="ui mini image" v-if="track.album && track.album.cover.original" v-lazy="$store.getters['instance/absoluteUrl'](track.album.cover.small_square_crop)">
      <img class="ui mini image" v-else src="../../../assets/audio/default-cover.png">
    </td>
    <td colspan="6">
      <router-link class="track" :to="{name: 'library.tracks.detail', params: {id: track.id }}">
        <template v-if="displayPosition && track.position">
          {{ track.position }}.
        </template>
        {{ track.title|truncate(40) }}
      </router-link>
    </td>
    <td colspan="4">
      <router-link class="artist discrete link" :to="{name: 'library.artists.detail', params: {id: track.artist.id }}">
        {{ track.artist.name|truncate(40) }}
      </router-link>
    </td>
    <td colspan="4">
      <router-link v-if="track.album" class="album discrete link" :to="{name: 'library.albums.detail', params: {id: track.album.id }}">
        {{ track.album.title|truncate(40) }}
      </router-link>
    </td>
    <td colspan="4" v-if="track.uploads && track.uploads.length > 0">
      <human-duration :duration="track.uploads[0].duration"></human-duration>
    </td>
    <td colspan="4" v-else>
      <translate translate-context="*/*/*">N/A</translate>
    </td>
    <td colspan="2" v-if="displayActions" class="align right">
      <play-button
        class="play-button basic icon"
        :dropdown-only="true"
        :is-playable="track.is_playable"
        :dropdown-icon-classes="['ellipsis', 'vertical', 'large really discrete']"
        :track="track"
      ></play-button>
      <track-playlist-icon
        v-if="$store.state.auth.authenticated"
        :track="track"></track-playlist-icon>
      <track-favorite-icon class="favorite-icon" :track="track"></track-favorite-icon>
    </td>
  </tr>
</template>

<script>
import { mapGetters } from "vuex"
import TrackFavoriteIcon from '@/components/favorites/TrackFavoriteIcon'
import TrackPlaylistIcon from '@/components/playlists/TrackPlaylistIcon'
import PlayButton from '@/components/audio/PlayButton'

export default {
  props: {
    track: {type: Object, required: true},
    artist: {type: Object, required: false},
    displayPosition: {type: Boolean, default: false},
    displayActions: {type: Boolean, default: true},
    playable: {type: Boolean, required: false, default: false},
  },
  components: {
    TrackFavoriteIcon,
    TrackPlaylistIcon,
    PlayButton
  },
  computed: {
    ...mapGetters({
      currentTrack: "queue/currentTrack",
    }),
    isPlaying () {
      return this.$store.state.player.playing
    },
    albumArtist () {
      if (this.artist) {
        return this.artist
      } else {
        return this.track.album.artist
      }
    },
  }
}
</script>
