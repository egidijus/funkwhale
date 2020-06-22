<template>
  <main>
    <div v-if="isLoading" class="ui vertical segment">
      <div :class="['ui', 'centered', 'active', 'inline', 'loader']"></div>
    </div>
    <template v-if="object">
      <section :class="['ui', 'head', 'vertical', 'stripe', 'segment']" v-title="object.artist.name">
        <div class="ui stackable one column grid">
          <div class="ui column">
            <div class="segment-content">
              <h2 class="ui header">
                <img v-if="object.artist.cover && object.artist.cover.square_crop" v-lazy="$store.getters['instance/absoluteUrl'](object.artist.cover.square_crop)">
                <img v-else src="../../assets/audio/default-cover.png">
                <div class="content">
                  {{ object.artist.name | truncate(100) }}
                  <div class="sub header">
                    <template v-if="object.artist.is_local">
                      <span class="ui tiny accent label">
                        <i class="home icon"></i>
                        <translate translate-context="Content/Moderation/*/Short, Noun">Local</translate>
                      </span>
                      &nbsp;
                    </template>
                  </div>
                </div>
              </h2>
              <template v-if="object.artist.tags && object.artist.tags.length > 0">
                <tags-list :limit="5" detail-route="manage.library.tags.detail" :tags="object.artist.tags"></tags-list>
                <div class="ui hidden divider"></div>
              </template>

              <div class="header-buttons">

                <div class="ui icon buttons">
                  <router-link class="ui labeled icon button" :to="{name: 'channels.detail', params: {id: object.uuid }}">
                    <i class="info icon"></i>
                    <translate translate-context="Content/Moderation/Link/Verb">Open local profile</translate>&nbsp;
                  </router-link>
                  <div class="ui floating dropdown icon button" v-dropdown>
                    <i class="dropdown icon"></i>
                    <div class="menu">
                      <a
                        v-if="$store.state.auth.profile && $store.state.auth.profile.is_superuser"
                        class="basic item"
                        :href="$store.getters['instance/absoluteUrl'](`/api/admin/audio/channel/${object.id}`)"
                        target="_blank" rel="noopener noreferrer">
                        <i class="wrench icon"></i>
                        <translate translate-context="Content/Moderation/Link/Verb">View in Django's admin</translate>&nbsp;
                      </a>
                      <fetch-button @refresh="fetchData" v-if="!object.actor.is_local" class="basic item" :url="`channels/${object.uuid}/fetches/`">
                        <i class="refresh icon"></i>&nbsp;
                        <translate translate-context="Content/Moderation/Button/Verb">Refresh from remote server</translate>&nbsp;
                      </fetch-button>
                      <a class="basic item" :href="object.actor.url || object.actor.fid" target="_blank" rel="noopener noreferrer">
                        <i class="external icon"></i>
                        <translate translate-context="Content/Moderation/Link/Verb">Open remote profile</translate>&nbsp;
                      </a>
                    </div>
                  </div>
                </div>
                <div class="ui buttons">
                  <dangerous-button
                    :class="['ui', {loading: isLoading}, 'basic danger button']"
                    :action="remove">
                    <translate translate-context="*/*/*/Verb">Delete</translate>
                    <p slot="modal-header"><translate translate-context="Popup/Library/Title">Delete this channel?</translate></p>
                    <div slot="modal-content">
                      <p><translate translate-context="Content/Moderation/Paragraph">The channel will be removed, as well as associated uploads, tracks, and albums. This action is irreversible.</translate></p>
                    </div>
                    <p slot="modal-confirm"><translate translate-context="*/*/*/Verb">Delete</translate></p>
                  </dangerous-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <div class="ui vertical stripe segment">
        <div class="ui stackable three column grid">
          <div class="column">
            <section>
              <h3 class="ui header">
                <i class="info icon"></i>
                <div class="content">
                  <translate translate-context="Content/Moderation/Title">Channel data</translate>
                </div>
              </h3>
              <table class="ui very basic table">
                <tbody>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*/Noun">Name</translate>
                    </td>
                    <td>
                      {{ object.artist.name }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.channels', query: {q: getQuery('category', object.artist.content_category) }}">
                        <translate translate-context="*/*/*">Category</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.artist.content_category }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.moderation.accounts.detail', params: {id: object.attributed_to.full_username }}">
                        <translate translate-context="*/*/*/Noun">Account</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.attributed_to.preferred_username }}
                    </td>
                  </tr>
                  <tr v-if="!object.actor.is_local">
                    <td>
                      <router-link :to="{name: 'manage.moderation.domains.detail', params: {id: object.actor.domain }}">
                        <translate translate-context="Content/Moderation/*/Noun">Domain</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.actor.domain }}
                    </td>
                  </tr>
                  <tr v-if="object.artist.description">
                    <td>
                      <translate translate-context="'*/*/*/Noun">Description</translate>
                    </td>
                    <td v-html="object.artist.description.html"></td>
                  </tr>
                  <tr v-if="object.actor.url">
                    <td>
                      <translate translate-context="'Content/*/*/Noun">URL</translate>
                    </td>
                    <td>
                      <a :href="object.actor.url" rel="noreferrer noopener" target="_blank">{{ object.actor.url }}</a>
                    </td>
                  </tr>
                  <tr v-if="object.rss_url">
                    <td>
                      <translate translate-context="'*/*/*">RSS Feed</translate>
                    </td>
                    <td>
                      <a :href="object.rss_url" rel="noreferrer noopener" target="_blank">{{ object.rss_url }}</a>
                    </td>
                  </tr>
                </tbody>
              </table>
            </section>
          </div>
          <div class="column">
            <section>
              <h3 class="ui header">
                <i class="feed icon"></i>
                <div class="content">
                  <translate translate-context="Content/Moderation/Title">Activity</translate>&nbsp;
                  <span :data-tooltip="labels.statsWarning"><i class="question circle icon"></i></span>

                </div>
              </h3>
              <div v-if="isLoadingStats" class="ui placeholder">
                <div class="full line"></div>
                <div class="short line"></div>
                <div class="medium line"></div>
                <div class="long line"></div>
              </div>
              <table v-else class="ui very basic table">
                <tbody>
                  <tr>
                    <td>
                      <translate translate-context="Content/Moderation/Table.Label/Short (Value is a date)">First seen</translate>
                    </td>
                    <td>
                      <human-date :date="object.creation_date"></human-date>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*/Noun">Listenings</translate>
                    </td>
                    <td>
                      {{ stats.listenings }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*">Favorited tracks</translate>
                    </td>
                    <td>
                      {{ stats.track_favorites }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*">Playlists</translate>
                    </td>
                    <td>
                      {{ stats.playlists }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.moderation.reports.list', query: {q: getQuery('target', `channel:${object.uuid}`) }}">
                        <translate translate-context="Content/Moderation/Table.Label/Noun">Linked reports</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ stats.reports }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.edits', query: {q: getQuery('target', 'artist ' + object.artist.id)}}">
                        <translate translate-context="*/Admin/*/Noun">Edits</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ stats.mutations }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </section>
          </div>
          <div class="column">
            <section>
              <h3 class="ui header">
                <i class="music icon"></i>
                <div class="content">
                  <translate translate-context="Content/Moderation/Title">Audio content</translate>&nbsp;
                  <span :data-tooltip="labels.statsWarning"><i class="question circle icon"></i></span>

                </div>
              </h3>
              <div v-if="isLoadingStats" class="ui placeholder">
                <div class="full line"></div>
                <div class="short line"></div>
                <div class="medium line"></div>
                <div class="long line"></div>
              </div>
              <table v-else class="ui very basic table">
                <tbody>

                  <tr>
                    <td>
                      <translate translate-context="Content/Moderation/Table.Label/Noun">Cached size</translate>
                    </td>
                    <td>
                      {{ stats.media_downloaded_size | humanSize }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="Content/Moderation/Table.Label">Total size</translate>
                    </td>
                    <td>
                      {{ stats.media_total_size | humanSize }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.uploads', query: {q: getQuery('channel_id', object.uuid) }}">
                        <translate translate-context="*/*/*">Uploads</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ stats.uploads }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.albums', query: {q: getQuery('channel_id', object.uuid) }}">
                        <translate translate-context="*/*/*">Albums</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.artist.albums_count }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.tracks', query: {q: getQuery('channel_id', object.uuid) }}">
                        <translate translate-context="*/*/*">Tracks</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.artist.tracks_count }}
                    </td>
                  </tr>
                </tbody>
              </table>

            </section>
          </div>
        </div>
      </div>

    </template>
  </main>
</template>

<script>
import axios from "axios"
import logger from "@/logging"

import TagsList from "@/components/tags/List"
import FetchButton from "@/components/federation/FetchButton"

export default {
  props: ["id"],
  components: {
    FetchButton,
    TagsList
  },
  data() {
    return {
      isLoading: true,
      isLoadingStats: false,
      object: null,
      stats: null,
    }
  },
  created() {
    this.fetchData()
    this.fetchStats()
  },
  methods: {
    fetchData() {
      var self = this
      this.isLoading = true
      let url = `manage/channels/${this.id}/`
      axios.get(url).then(response => {
        self.object = response.data
        self.isLoading = false
      })
    },
    fetchStats() {
      var self = this
      this.isLoadingStats = true
      let url = `manage/channels/${this.id}/stats/`
      axios.get(url).then(response => {
        self.stats = response.data
        self.isLoadingStats = false
      })
    },
    remove () {
      var self = this
      this.isLoading = true
      let url = `manage/channels/${this.id}/`
      axios.delete(url).then(response => {
        self.$router.push({name: 'manage.channels'})
      })
    },
    getQuery (field, value) {
      return `${field}:"${value}"`
    }
  },
  computed: {
    labels() {
      return {
        statsWarning: this.$pgettext('Content/Moderation/Help text', 'Statistics are computed from known activity and content on your instance, and do not reflect general activity for this object'),
      }
    },
  }
}
</script>
