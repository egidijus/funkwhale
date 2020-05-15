<template>
  <main>
    <div v-if="isLoading" class="ui vertical segment">
      <div :class="['ui', 'centered', 'active', 'inline', 'loader']"></div>
    </div>
    <template v-if="object">
      <section :class="['ui', 'head', 'vertical', 'stripe', 'segment']" v-title="object.name">
        <div class="ui stackable one column grid">
          <div class="ui column">
            <div class="segment-content">
              <h2 class="ui header">
                <i class="circular inverted hashtag icon"></i>
                <div class="content">
                  {{ object.name | truncate(100) }}
                </div>
              </h2>
              <div class="header-buttons">

                <div class="ui icon buttons">
                  <router-link class="ui labeled icon button" :to="{name: 'library.tags.detail', params: {id: object.name }}">
                    <i class="info icon"></i>
                    <translate translate-context="Content/Moderation/Link/Verb">Open local profile</translate>&nbsp;
                  </router-link>
                  <div class="ui floating dropdown icon button" v-dropdown>
                    <i class="dropdown icon"></i>
                    <div class="menu">
                      <a
                        v-if="$store.state.auth.profile && $store.state.auth.profile.is_superuser"
                        class="basic item"
                        :href="$store.getters['instance/absoluteUrl'](`/api/admin/tags/tag/${object.id}`)"
                        target="_blank" rel="noopener noreferrer">
                        <i class="wrench icon"></i>
                        <translate translate-context="Content/Moderation/Link/Verb">View in Django's admin</translate>&nbsp;
                      </a>
                    </div>
                  </div>
                </div>
                <div class="ui buttons">
                  <dangerous-button
                    :class="['ui', {loading: isLoading}, 'basic danger button']"
                    :action="remove">
                    <translate translate-context="*/*/*/Verb">Delete</translate>
                    <p slot="modal-header"><translate translate-context="Popup/Library/Title">Delete this tag?</translate></p>
                    <div slot="modal-content">
                      <p><translate translate-context="Content/Moderation/Paragraph">The tag will be removed and unlinked from any existing entity. This action is irreversible.</translate></p>
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
                  <translate translate-context="Content/Moderation/Title">Tag data</translate>
                </div>
              </h3>
              <table class="ui very basic table">
                <tbody>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*/Noun">Name</translate>
                    </td>
                    <td>
                      {{ object.name }}
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
              <table class="ui very basic table">
                <tbody>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.artists', query: {q: getQuery('tag', object.name) }}">
                        <translate translate-context="*/*/*/Noun">Artists</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.artists_count }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.albums', query: {q: getQuery('tag', object.name) }}">
                        <translate translate-context="*/*/*">Albums</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.albums_count }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.tracks', query: {q: getQuery('tag', object.name) }}">
                        <translate translate-context="*/*/*">Tracks</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.tracks_count }}
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

import FetchButton from "@/components/federation/FetchButton"

export default {
  props: ["id"],
  components: {
    FetchButton
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
  },
  methods: {
    fetchData() {
      var self = this
      this.isLoading = true
      let url = `manage/tags/${this.id}/`
      axios.get(url).then(response => {
        self.object = response.data
        self.isLoading = false
      })
    },
    remove () {
      var self = this
      this.isLoading = true
      let url = `manage/tags/${this.id}/`
      axios.delete(url).then(response => {
        self.$router.push({name: 'manage.library.tags'})
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
