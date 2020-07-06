<template>
  <main :class="[theme]">
    <!-- SVG from https://cdn.plyr.io/3.4.7/plyr.svg -->
    <svg aria-hidden="true" style="display: none" xmlns="http://www.w3.org/2000/svg">
      <symbol id="plyr-download"><path d="M9 13c.3 0 .5-.1.7-.3L15.4 7 14 5.6l-4 4V1H8v8.6l-4-4L2.6 7l5.7 5.7c.2.2.4.3.7.3zM2 15h14v2H2z"/></symbol>
      <symbol id="plyr-enter-fullscreen"><path d="M10 3h3.6l-4 4L11 8.4l4-4V8h2V1h-7zM7 9.6l-4 4V10H1v7h7v-2H4.4l4-4z"/></symbol>
      <symbol id="plyr-exit-fullscreen"><path d="M1 12h3.6l-4 4L2 17.4l4-4V17h2v-7H1zM16 .6l-4 4V1h-2v7h7V6h-3.6l4-4z"/></symbol>
      <symbol id="plyr-fast-forward"><path d="M7.875 7.171L0 1v16l7.875-6.171V17L18 9 7.875 1z"/></symbol>
      <symbol id="plyr-muted"><path d="M12.4 12.5l2.1-2.1 2.1 2.1 1.4-1.4L15.9 9 18 6.9l-1.4-1.4-2.1 2.1-2.1-2.1L11 6.9 13.1 9 11 11.1zM3.786 6.008H.714C.286 6.008 0 6.31 0 6.76v4.512c0 .452.286.752.714.752h3.072l4.071 3.858c.5.3 1.143 0 1.143-.602V2.752c0-.601-.643-.977-1.143-.601L3.786 6.008z"/></symbol>
      <symbol id="plyr-pause"><path d="M6 1H3c-.6 0-1 .4-1 1v14c0 .6.4 1 1 1h3c.6 0 1-.4 1-1V2c0-.6-.4-1-1-1zM12 1c-.6 0-1 .4-1 1v14c0 .6.4 1 1 1h3c.6 0 1-.4 1-1V2c0-.6-.4-1-1-1h-3z"/></symbol>
      <symbol id="plyr-pip"><path d="M13.293 3.293L7.022 9.564l1.414 1.414 6.271-6.271L17 7V1h-6z"/><path d="M13 15H3V5h5V3H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-6h-2v5z"/></symbol>
      <symbol id="plyr-play"><path d="M15.562 8.1L3.87.225C3.052-.337 2 .225 2 1.125v15.75c0 .9 1.052 1.462 1.87.9L15.563 9.9c.584-.45.584-1.35 0-1.8z"/></symbol>
      <symbol id="plyr-restart"><path d="M9.7 1.2l.7 6.4 2.1-2.1c1.9 1.9 1.9 5.1 0 7-.9 1-2.2 1.5-3.5 1.5-1.3 0-2.6-.5-3.5-1.5-1.9-1.9-1.9-5.1 0-7 .6-.6 1.4-1.1 2.3-1.3l-.6-1.9C6 2.6 4.9 3.2 4 4.1 1.3 6.8 1.3 11.2 4 14c1.3 1.3 3.1 2 4.9 2 1.9 0 3.6-.7 4.9-2 2.7-2.7 2.7-7.1 0-9.9L16 1.9l-6.3-.7z"/></symbol>
      <symbol id="plyr-rewind"><path d="M10.125 1L0 9l10.125 8v-6.171L18 17V1l-7.875 6.171z"/></symbol>
      <symbol id="plyr-settings"><path d="M16.135 7.784a2 2 0 0 1-1.23-2.969c.322-.536.225-.998-.094-1.316l-.31-.31c-.318-.318-.78-.415-1.316-.094a2 2 0 0 1-2.969-1.23C10.065 1.258 9.669 1 9.219 1h-.438c-.45 0-.845.258-.997.865a2 2 0 0 1-2.969 1.23c-.536-.322-.999-.225-1.317.093l-.31.31c-.318.318-.415.781-.093 1.317a2 2 0 0 1-1.23 2.969C1.26 7.935 1 8.33 1 8.781v.438c0 .45.258.845.865.997a2 2 0 0 1 1.23 2.969c-.322.536-.225.998.094 1.316l.31.31c.319.319.782.415 1.316.094a2 2 0 0 1 2.969 1.23c.151.607.547.865.997.865h.438c.45 0 .845-.258.997-.865a2 2 0 0 1 2.969-1.23c.535.321.997.225 1.316-.094l.31-.31c.318-.318.415-.781.094-1.316a2 2 0 0 1 1.23-2.969c.607-.151.865-.547.865-.997v-.438c0-.451-.26-.846-.865-.997zM9 12a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"/></symbol>
      <symbol id="plyr-volume"><path d="M15.6 3.3c-.4-.4-1-.4-1.4 0-.4.4-.4 1 0 1.4C15.4 5.9 16 7.4 16 9c0 1.6-.6 3.1-1.8 4.3-.4.4-.4 1 0 1.4.2.2.5.3.7.3.3 0 .5-.1.7-.3C17.1 13.2 18 11.2 18 9s-.9-4.2-2.4-5.7z"/><path d="M11.282 5.282a.909.909 0 0 0 0 1.316c.735.735.995 1.458.995 2.402 0 .936-.425 1.917-.995 2.487a.909.909 0 0 0 0 1.316c.145.145.636.262 1.018.156a.725.725 0 0 0 .298-.156C13.773 11.733 14.13 10.16 14.13 9c0-.17-.002-.34-.011-.51-.053-.992-.319-2.005-1.522-3.208a.909.909 0 0 0-1.316 0zM3.786 6.008H.714C.286 6.008 0 6.31 0 6.76v4.512c0 .452.286.752.714.752h3.072l4.071 3.858c.5.3 1.143 0 1.143-.602V2.752c0-.601-.643-.977-1.143-.601L3.786 6.008z"/></symbol>
      <!-- those ones are from fork-awesome -->
      <symbol id="plyr-step-backward"><path d="M979 141c25-25 45-16 45 19v1472c0 35-20 44-45 19L269 941c-6-6-10-12-13-19v678c0 35-29 64-64 64H64c-35 0-64-29-64-64V192c0-35 29-64 64-64h128c35 0 64 29 64 64v678c3-7 7-13 13-19z"/></symbol>
      <symbol id="plyr-step-forward"><path d="M45 1651c-25 25-45 16-45-19V160c0-35 20-44 45-19l710 710c6 6 10 12 13 19V192c0-35 29-64 64-64h128c35 0 64 29 64 64v1408c0 35-29 64-64 64H832c-35 0-64-29-64-64V922c-3 7-7 13-13 19z"/></symbol>
    </svg>
    <article>
      <aside class="cover main" v-if="currentTrack">
        <img height="120" v-if="currentTrack.cover" :src="currentTrack.cover" alt="Cover" />
        <img height="120" v-else src="./assets/embed/default-cover.jpeg" alt="Cover" />
      </aside>
      <div class="content" aria-label="Track information">
        <header v-if="currentTrack">
          <h3><a :href="fullUrl('/library/tracks/' + currentTrack.id)" target="_blank" rel="noopener noreferrer">{{ currentTrack.title }}</a></h3>
          <a :href="fullUrl('/library/artists/' + currentTrack.artist.id)" target="_blank" rel="noopener noreferrer">{{ currentTrack.artist.name }}</a>
        </header>
        <section v-if="!isLoading" class="controls" aria-label="Audio player">
          <template v-if="currentTrack && currentTrack.sources.length > 0">
            <div class="queue-controls plyr--audio" v-if="tracks.length > 1">
              <div class="plyr__controls">
                <button
                  @focus="setControlFocus($event, true)"
                  @blur="setControlFocus($event, false)"
                  @click="previous()"
                  type="button"
                  class="plyr__control"
                  aria-label="Play previous track">
                  <svg class="icon--not-pressed" role="presentation" focusable="false" viewBox="0 0 1100 1650" width="80" height="80">
                    <use xlink:href="#plyr-step-backward"></use>
                  </svg>
                </button>
                <button
                  @click="next()"
                  @focus="setControlFocus($event, true)"
                  @blur="setControlFocus($event, false)"
                  type="button"
                  class="plyr__control"
                  aria-label="Play next track">
                  <svg class="icon--not-pressed" role="presentation" focusable="false" viewBox="0 0 1100 1650" width="80" height="80">
                    <use xlink:href="#plyr-step-forward"></use>
                  </svg>
                </button>
              </div>
            </div>

            <vue-plyr
              :key="currentIndex"
              ref="player"
              class="player"
              :options="{loadSprite: false, controls: controls, duration: currentTrack.sources[0].duration, autoplay}">
              <audio preload="none">
                <source v-for="source in currentTrack.sources" :src="source.src" :type="source.type"/>
              </audio>
            </vue-plyr>
          </template>
          <div v-else class="player">
            <span v-if="error === 'invalid_type'" class="error">Widget improperly configured (bad resource type {{ type }}).</span>
            <span v-else-if="error === 'invalid_id'" class="error">Widget improperly configured (missing resource id).</span>
            <span v-else-if="error === 'server_not_found'" class="error">Track not found.</span>
            <span v-else-if="error === 'server_requires_auth'" class="error">You need to login to access this resource.</span>
            <span v-else-if="error === 'server_error'" class="error">A server error occurred.</span>
            <span v-else-if="error === 'server_error'" class="error">An unknown error occurred while loading track data from server.</span>
            <span v-else-if="currentTrack && currentTrack.sources.length === 0" class="error">This track is unavailable.</span>
            <span v-else class="error">An unknown error occurred while loading track data.</span>
          </div>
          <a title="Funkwhale" href="https://funkwhale.audio" target="_blank" rel="noopener noreferrer" class="logo-wrapper">
            <logo :fill="currentTheme.textColor" class="logo"></logo>
          </a>
        </section>
      </div>
    </article>
    <div v-if="tracks.length > 1" class="queue-wrapper" id="queue">
      <table class="queue">
        <tbody>
          <tr
            :id="'queue-item-' + index"
            role="button"
            v-if="track.sources.length > 0"
            :key="index"
            :class="[{active: index === currentIndex}]"
            @click="play(index)"
            @keyup.enter="play(index)"
            v-for="(track, index) in tracks">
            <td class="position-cell" width="40">
              <span class="position">
                {{ index + 1 }}
              </span>
            </td>
            <td class="title" :title="track.title" ><div colspan="2" class="ellipsis">{{ track.title }}</div></td>
            <td class="artist" :title="track.artist.name" ><div class="ellipsis">{{ track.artist.name }}</div></td>
            <td class="album">
              <div class="ellipsis" v-if="track.album" :title="track.album.title">{{ track.album.title }}</div>
            </td>
            <td width="50">{{ time.durationFormatted(track.sources[0].duration) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>

<script>
import axios from 'axios'
import Logo from "@/components/Logo"
import url from '@/utils/url'
import time from '@/utils/time'

function getURLParams () {
  var urlParams
  var match,
      pl     = /\+/g,  // Regex for replacing addition symbol with a space
      search = /([^&=]+)=?([^&]*)/g,
      decode = function (s) { return decodeURIComponent(s.replace(pl, " ")); },
      query  = window.location.search.substring(1);

  urlParams = {};
  while (match = search.exec(query))
      urlParams[decode(match[1])] = decode(match[2]);
  return urlParams
}
export default {
  name: 'app',
  components: {Logo},
  data () {
    return {
      time,
      supportedTypes: ['track', 'album', 'artist', 'playlist', 'channel'],
      baseUrl: '',
      error: null,
      type: null,
      id: null,
      tracks: [],
      autoplay: false,
      url: null,
      isLoading: true,
      theme: 'dark',
      currentIndex: -1,
      themes: {
        dark: {
          textColor: 'white',
        }
      }
    }
  },
  created () {
    let params = getURLParams()
    this.baseUrl = params.b || ''
    this.type = params.type
    if (this.supportedTypes.indexOf(this.type) === -1) {
      this.error = 'invalid_type'
    }
    this.id = params.id
    if (!this.id) {
      this.error = 'invalid_id'
    }
    if (this.error) {
      this.isLoading = false
      return
    }
    if (!!params.instance) {
      this.baseUrl = params.instance
    }

    this.autoplay = params.autoplay != undefined || params.auto_play != undefined
    this.fetch(this.type, this.id)
  },
  mounted () {
    var parser = document.createElement('a')
    parser.href = this.baseUrl
    this.url = parser
  },
  computed: {
    currentTrack () {
      if (this.tracks.length === 0) {
        return null
      }
      return this.tracks[this.currentIndex]
    },
    currentTheme () {
      return this.themes[this.theme]
    },
    controls () {
      return  [
        'play', // Play/pause playback
        'progress', // The progress bar and scrubber for playback and buffering
        'current-time', // The current time of playback
        'mute', // Toggle mute
        'volume', // Volume control
      ]
    },
    hasPrevious () {
      return this.currentIndex > 0
    },
    hasNext () {
      return this.currentIndex < this.tracks.length - 1
    },
  },
  methods: {
    next () {
      if (this.hasNext) {
        this.play(this.currentIndex + 1)
      }
    },
    previous () {
      if (this.hasPrevious) {
        this.play(this.currentIndex - 1)
      }
    },
    setControlFocus(event, enable) {
      if (enable) {
        event.target.classList.add("plyr__tab-focus");
      } else {
        event.target.classList.remove("plyr__tab-focus");
      }
    },
    fetch (type, id) {
      if (type === 'track') {
        this.fetchTrack(id)
      }
      if (type === 'album') {
        this.fetchTracks({album: id, playable: true, ordering: "disc_number,position"})
      }
      if (type === 'channel') {
        this.fetchTracks({channel: id, playable: true, include_channels: 'true', ordering: "-creation_date"})
      }
      if (type === 'artist') {
        this.fetchTracks({artist: id, playable: true, include_channels: 'true', ordering: "-release_date,disc_number,position"})
      }
      if (type === 'playlist') {
        this.fetchTracks({}, `/api/v1/playlists/${id}/tracks/`)
      }
    },
    play (index) {
      this.currentIndex = index
      let self = this
      this.$nextTick(() => {
        self.$refs.player.player.play()
      })
    },
    fetchTrack (id) {
      let self = this
      let url = `${this.baseUrl}/api/v1/tracks/${id}/`
      axios.get(url).then(response => {
        self.tracks = self.parseTracks([response.data])
        self.isLoading = false;
      }).catch(error => {
        if (error.response) {
          if (error.response.status === 404) {
            self.error = 'server_not_found'
          }
          else if (error.response.status === 403) {
            self.error = 'server_requires_auth'
          }
          else if (error.response.status === 500) {
            self.error = 'server_error'
          }
          else {
            self.error = 'server_unknown_error'
          }
        } else {
          self.error = 'server_unknown_error'
        }
        self.isLoading = false;
      })
    },
    fetchTracks (filters, path) {
      path = path || "/api/v1/tracks/"
      let self = this
      let url = `${this.baseUrl}${path}`
      axios.get(url, {params: filters}).then(response => {
        self.tracks = self.parseTracks(response.data.results)
        self.isLoading = false;
      }).catch(error => {
        if (error.response) {
          if (error.response.status === 404) {
            self.error = 'server_not_found'
          }
          else if (error.response.status === 403) {
            self.error = 'server_requires_auth'
          }
          else if (error.response.status === 500) {
            self.error = 'server_error'
          }
          else {
            self.error = 'server_unknown_error'
          }
        } else {
          self.error = 'server_unknown_error'
        }
        self.isLoading = false;
      })
    },
    parseTracks (tracks) {
      let self = this
      if (this.type === 'playlist') {
        tracks = tracks.map((t) => {
          return t.track
        })
      }
      return tracks.map(t => {
        return {
          id: t.id,
          title: t.title,
          artist: t.artist,
          album: t.album,
          cover: self.getCover((t.album || {}).cover),
          sources: self.getSources(t.uploads)
        }
      })
    },
    bindEvents () {
      let self = this
      this.$refs.player.player.on('ended', () => {
        self.next()
      })
    },
    fullUrl (path) {
      if (path.startsWith('/')) {
        return this.baseUrl + path
      }
      return path
    },
    getCover(albumCover) {
      if (albumCover) {
        return albumCover.medium_square_crop
      }
    },
    getSources (uploads) {
      let self = this;
      let sources = uploads.map(u => {
        return {
          type: u.mimetype,
          src: self.fullUrl(u.listen_url),
          duration: u.duration
        }
      })
      if (sources.length > 0) {
        // We always add a transcoded MP3 src at the end
        // because transcoding is expensive, but we want browsers that do
        // not support other codecs to be able to play it :)
        sources.push({
          type: 'audio/mpeg',
          src: url.updateQueryString(
            self.fullUrl(sources[0].src),
            'to',
            'mp3'
          )
        })
      }
      return sources
    }
  },
  watch: {
    currentIndex (v) {
      // we bind player events
      let self = this
      this.$nextTick(() => {
        self.bindEvents()
        if (self.tracks.length > 0) {
          let el = document.getElementById(`queue-item-${v}`);
          if (!el) {
            return
          }
          var topPos = el.offsetTop;
          document.getElementById('queue').scrollTop = topPos-10;
        }
      })
    },
    tracks () {
      this.currentIndex = 0
    }
  }
}
</script>

<style lang="scss">
@import "~plyr/src/sass/plyr.scss";

html,
body,
main {
  height: 100%;
}
body {
  margin: 0;
  font-family: sans-serif;
}
main {
  display: flex;
  flex-direction: column;
}
article {
  display: flex;
  position: relative;
  aside {
    padding: 0.5em;
  }
}

a {
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
section.controls {
  display: flex;
  width: 100%;
}
.cover {
  max-width: 120px;
  max-height: 120px;
}

.player {
  flex: 1;
  align-self: flex-end;
}
.player .plyr {
  min-width: inherit;
}
article .content {
  flex: 1;
  display: flex;
  flex-direction: column;
  h3 {
    margin: 0 0 0.5em;
  }
  header {
    flex: 1;
    padding: 1em;
  }
}
.player,
.queue-controls {
  padding: 0.25em 0;
  margin-right: 0.25em;
  align-self: center;
}
section .plyr--audio .plyr__controls {
  padding: 0;
}

.error {
  font-weight: bold;
  display: block;
  text-align: center;
}
.logo-wrapper {
  height: 2em;
  width: 2em;
  padding: 0.25em;
  margin-left: 0.5em;
  display: block;
}
[role="button"] {
  cursor: pointer;
}
.ellipsis {
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.queue-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 0.5em;
}
.queue {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  margin-bottom: 0.5em;
  td {
    padding: 0.5em;
    font-size: 90%;
    img {
      vertical-align: middle;
      margin-right: 1em;
    }
  }
  td:last-child {
    text-align: right;
  }
  .position {
    padding: 0.1em 0.3em;
    display: inline-block;
  }
}
@media screen and (max-width: 640px) {
  .queue .album {
    display: none;
  }
  .plyr__controls .plyr__time {
    display: none;
  }
}
@media screen and (max-width: 460px) {
  article,
  article .content {
    position: relative;
    display: block;
  }
  .content header {
    padding-right: 80px;
  }
  .cover.main {
    position: absolute;
    right: 0;
    top: 0;
    img {
      height: 60px;
      width: 60px;
    }
  }
}

@media screen and (max-width: 320px) {
  .content header {
    font-size: 14px;
  }
  .content h3 {
    font-size: 15px;
  }
  .logo-wrapper,
  .position-cell {
    display: none;
  }
  .plyr__volume {
    min-width: 70px;
  }
  .queue .artist {
    display: none;
  }
}

@media screen and (max-width: 200px) {
  .content header {
    padding-right: 1em;
    font-size: 13px;
  }
  .content h3 {
    font-size: 14px;
  }
  .cover.main {
    display: none;
  }
  .plyr__progress {
    display: none;
  }
  .controls .plyr__control,
  .player .plyr__control {
    padding: 3px;
  }
  .queue td:last-child {
    display: none;
  }
}

@media screen and (max-width: 170px) {
  .plyr__volume {
    min-width: inherit;
  }
}

@media screen and (max-height: 180px) {
  .queue-wrapper {
    display: none;
  }
  article .content {
    display: flex;
    align-items: flex-start;
    width: 100%;
    height: 100vh;
  }
  article .content header {
    flex-grow: 1;
  }
}
// themes

.dark {
  $primary-color: rgb(242, 113, 28);
  $dark: rgb(27, 28, 29);
  $lighter: rgb(47, 48, 48);
  $clear: rgb(242, 242, 242);
  // $primary-color: rgb(255, 88, 78);
  .logo-wrapper {
    background-color: $primary-color;
  }
  .plyr--audio .plyr__control.plyr__tab-focus,
  .plyr--audio .plyr__control:hover,
  .plyr--audio .plyr__control[aria-expanded="true"] {
    background-color: $primary-color;
  }
  .plyr--audio .plyr__control.plyr__tab-focus,
  .plyr--audio .plyr__control:hover,
  .plyr--audio .plyr__control[aria-expanded="true"] {
    background-color: $primary-color;
  }
  .plyr--full-ui input[type="range"] {
    color: $primary-color;
  }
  article,
  .player,
  .plyr--audio .plyr__controls {
    background-color: $dark;
  }
  .queue-wrapper {
    background-color: $lighter;
  }
  article,
  article a,
  .player,
  .queue tr,
  .plyr--audio .plyr__controls {
    color: white;
  }
  .plyr__control.plyr__tab-focus {
    -webkit-box-shadow: 0 0 0 2px rgba(26, 175, 255, 0.5);
    box-shadow: 0 0 0 2px rgba(26, 175, 255, 0.5);
    outline: 0;
  }
  tr:hover,
  tr:focus {
    background-color: $dark;
  }
  tr.active {
    background-color: $clear;
    color: $dark;
  }

  tr.active {
    .position {
      background-color: $primary-color;
      color: $clear;
    }
  }
}
</style>
