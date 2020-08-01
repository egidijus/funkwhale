<template>
  <div class="component-track-widget">
    <h3 v-if="!!this.$slots.title">
      <slot name="title"></slot>
      <span v-if="showCount" class="ui tiny circular label">{{ count }}</span>
    </h3>
    <div v-if="count > 0" class="ui divided unstackable items">
      <div :class="['item', itemClasses]" v-for="object in objects" :key="object.id">
        <div class="ui tiny image">
          <img v-if="object.track.album && object.track.album.cover.original" v-lazy="$store.getters['instance/absoluteUrl'](object.track.album.cover.medium_square_crop)">
          <img v-else src="../../../assets/audio/default-cover.png">
          <play-button class="play-overlay" :icon-only="true" :button-classes="['ui', 'circular', 'tiny', 'vibrant', 'icon', 'button']" :track="object.track"></play-button>
        </div>
        <div class="middle aligned content">
          <div class="ui unstackable grid">
            <div class="thirteen wide stretched column">
              <div class="ellipsis">
                <router-link :to="{name: 'library.tracks.detail', params: {id: object.track.id}}">
                  {{ object.track.title }}
                </router-link>
              </div>
              <div class="meta ellipsis">
                <span>
                  <router-link class="discrete link" :to="{name: 'library.artists.detail', params: {id: object.track.artist.id}}">
                    {{ object.track.artist.name }}
                  </router-link>
                </span>
              </div>
              <tags-list label-classes="tiny" :truncate-size="20" :limit="2" :show-more="false" :tags="object.track.tags"></tags-list>

              <div class="extra" v-if="isActivity">
                <router-link class="left floated" :to="{name: 'profile.overview', params: {username: object.user.username}}">@{{ object.user.username }}</router-link>
                <span class="right floated"><human-date :date="object.creation_date" /></span>
              </div>
            </div>
            <div class="one wide stretched column">
              <play-button
                class="basic icon"
                :account="object.actor"
                :dropdown-only="true"
                :dropdown-icon-classes="['ellipsis', 'vertical', 'large really discrete']"
                :track="object.track"></play-button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="isLoading" class="ui inverted active dimmer">
        <div class="ui loader"></div>
      </div>
    </div>
    <div v-else class="ui placeholder segment">
      <div class="ui icon header">
        <i class="music icon"></i>
        <translate translate-context="Content/Home/Placeholder">
          Nothing found
        </translate>
      </div>
      <div v-if="isLoading" class="ui inverted active dimmer">
        <div class="ui loader"></div>
      </div>
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
import PlayButton from '@/components/audio/PlayButton'
import TagsList from "@/components/tags/List"

export default {
  props: {
    filters: {type: Object, required: true},
    url: {type: String, required: true},
    isActivity: {type: Boolean, default: true},
    showCount: {type: Boolean, default: false},
    limit: {type: Number, default: 5},
    itemClasses: {type: String, default: ''},
  },
  components: {
    PlayButton,
    TagsList
  },
  data () {
    return {
      objects: [],
      count: 0,
      isLoading: false,
      errors: null,
      previousPage: null,
      nextPage: null
    }
  },
  created () {
    this.fetchData(this.url)
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
        self.count = response.data.count
        let newObjects
        if (self.isActivity) {
          // we have listening/favorites objects, not directly tracks
          newObjects = response.data.results
        } else {
          newObjects = response.data.results.map((r) => {
            return {track: r}
          })
        }
        self.objects = [...self.objects, ...newObjects]
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
    },
    count (v) {
      this.$emit('count', v)
    }
  }
}
</script>
