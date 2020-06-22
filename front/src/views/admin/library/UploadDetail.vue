<template>
  <main>
    <div v-if="isLoading" class="ui vertical segment">
      <div :class="['ui', 'centered', 'active', 'inline', 'loader']"></div>
    </div>
    <template v-if="object">
      <import-status-modal :upload="object" :show.sync="showUploadDetailModal" />
      <section :class="['ui', 'head', 'vertical', 'stripe', 'segment']" v-title="displayName(object)">
        <div class="ui stackable one column grid">
          <div class="ui column">
            <div class="segment-content">
              <h2 class="ui header">
                <i class="circular inverted file icon"></i>
                <div class="content">
                  {{ displayName(object) | truncate(100) }}
                  <div class="sub header">
                    <template v-if="object.is_local">
                      <span class="ui tiny accent label">
                        <i class="home icon"></i>
                        <translate translate-context="Content/Moderation/*/Short, Noun">Local</translate>
                      </span>
                      &nbsp;
                    </template>
                  </div>
                </div>
              </h2>
              <div class="header-buttons">

                <div class="ui icon buttons">
                  <a
                    v-if="$store.state.auth.profile && $store.state.auth.profile.is_superuser"
                    class="ui labeled icon button"
                    :href="$store.getters['instance/absoluteUrl'](`/api/admin/music/upload/${object.id}`)"
                    target="_blank" rel="noopener noreferrer">
                    <i class="wrench icon"></i>
                    <translate translate-context="Content/Moderation/Link/Verb">View in Django's admin</translate>&nbsp;
                  </a>
                  <div class="ui floating dropdown icon button" v-dropdown>
                    <i class="dropdown icon"></i>
                    <div class="menu">
                      <a
                        v-if="$store.state.auth.profile && $store.state.auth.profile.is_superuser"
                        class="basic item"
                        :href="$store.getters['instance/absoluteUrl'](`/api/admin/music/upload/${object.id}`)"
                        target="_blank" rel="noopener noreferrer">
                        <i class="wrench icon"></i>
                        <translate translate-context="Content/Moderation/Link/Verb">View in Django's admin</translate>&nbsp;
                      </a>
                      <a class="basic item" :href="object.url || object.fid" target="_blank" rel="noopener noreferrer">
                        <i class="external icon"></i>
                        <translate translate-context="Content/Moderation/Link/Verb">Open remote profile</translate>&nbsp;
                      </a>
                    </div>
                  </div>
                </div>
                <div class="ui buttons">
                  <a class="ui labeled icon button" v-if="object.audio_file" :href="$store.getters['instance/absoluteUrl'](object.audio_file)" target="_blank" rel="noopener noreferrer">
                    <i class="download icon"></i>
                    <translate translate-context="Content/Track/Link/Verb">Download</translate>
                  </a>
                </div>
                <div class="ui buttons">
                  <dangerous-button
                    :class="['ui', {loading: isLoading}, 'basic danger button']"
                    :action="remove">
                    <translate translate-context="*/*/*/Verb">Delete</translate>
                    <p slot="modal-header"><translate translate-context="Popup/Library/Title">Delete this upload?</translate></p>
                    <div slot="modal-content">
                      <p><translate translate-context="Content/Moderation/Paragraph">The upload will be removed. This action is irreversible.</translate></p>
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
                  <translate translate-context="Content/Moderation/Title">Upload data</translate>
                </div>
              </h3>
              <table class="ui very basic table">
                <tbody>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*/Noun">Name</translate>
                    </td>
                    <td>
                      {{ displayName(object) }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.uploads', query: {q: getQuery('privacy_level', object.library.privacy_level) }}">
                        <translate translate-context="*/*/*">Visibility</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ sharedLabels.fields.privacy_level.shortChoices[object.library.privacy_level] }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.moderation.accounts.detail', params: {id: object.library.actor.full_username }}">
                        <translate translate-context="*/*/*/Noun">Account</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.library.actor.preferred_username }}
                    </td>
                  </tr>
                  <tr v-if="!object.is_local">
                    <td>
                      <router-link :to="{name: 'manage.moderation.domains.detail', params: {id: object.domain }}">
                        <translate translate-context="Content/Moderation/*/Noun">Domain</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.domain }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.uploads', query: {q: getQuery('status', object.import_status) }}">
                        <translate translate-context="Content/*/*/Noun">Import status</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ sharedLabels.fields.import_status.choices[object.import_status].label }}
                      <button class="ui tiny basic icon button" :title="sharedLabels.fields.import_status.detailTitle" @click="detailedUpload = object; showUploadDetailModal = true">
                        <i class="question circle outline icon"></i>
                      </button>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.libraries.detail', params: {id: object.library.uuid }}">
                        <translate translate-context="*/*/*/Noun">Library</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.library.name }}
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
                </div>
              </h3>
              <table class="ui very basic table">
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
                      <translate translate-context="Content/*/*/Noun">Accessed date</translate>
                    </td>
                    <td>
                      <human-date v-if="object.accessed_date" :date="object.accessed_date"></human-date>
                      <translate v-else translate-context="*/*/*">N/A</translate>
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
                </div>
              </h3>
              <table class="ui very basic table">
                <tbody>
                  <tr v-if="object.track">
                    <td>
                      <router-link :to="{name: 'manage.library.tracks.detail', params: {id: object.track.id }}">
                        <translate translate-context="*/*/*/Noun">Track</translate>
                      </router-link>
                    </td>
                    <td>
                      {{ object.track.title }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="Content/Moderation/Table.Label/Noun">Cached size</translate>
                    </td>
                    <td>
                      <template v-if="object.audio_file">
                        {{ object.size | humanSize }}
                      </template>
                      <translate v-else translate-context="*/*/*">N/A</translate>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="Content/*/*/Noun">Size</translate>
                    </td>
                    <td>
                      {{ object.size | humanSize }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="Content/Track/*/Noun">Bitrate</translate>
                    </td>
                    <td>
                      <template v-if="object.bitrate">
                        {{ object.bitrate | humanSize }}/s
                      </template>
                      <translate v-else translate-context="*/*/*">N/A</translate>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="Content/*/*">Duration</translate>
                    </td>
                    <td>
                      <template v-if="object.duration">
                        {{ object.duration | duration }}
                      </template>
                      <translate v-else translate-context="*/*/*">N/A</translate>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <router-link :to="{name: 'manage.library.uploads', query: {q: getQuery('type', object.mimetype) }}">
                        <translate translate-context="Content/Track/Table.Label/Noun">Type</translate>
                      </router-link>
                    </td>
                    <td>
                      <template v-if="object.mimetype">
                        {{ object.mimetype }}
                      </template>
                      <translate v-else translate-context="*/*/*">N/A</translate>
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
import TranslationsMixin from "@/components/mixins/Translations"
import ImportStatusModal from '@/components/library/ImportStatusModal'
import time from '@/utils/time'


export default {
  props: ["id"],
  mixins: [
    TranslationsMixin,
  ],
  components: {
    ImportStatusModal
  },
  data() {
    return {
      time,
      detailedUpload: null,
      showUploadDetailModal: false,
      isLoading: true,
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
      let url = `manage/library/uploads/${this.id}/`
      axios.get(url).then(response => {
        self.object = response.data
        self.isLoading = false
      })
    },
    remove () {
      var self = this
      this.isLoading = true
      let url = `manage/library/uploads/${this.id}/`
      axios.delete(url).then(response => {
        self.$router.push({name: 'manage.library.uploads'})
      })
    },
    getQuery (field, value) {
      return `${field}:"${value}"`
    },
    displayName (upload) {
      if (upload.filename) {
        return upload.filename
      }
      if (upload.source) {
        return upload.source
      }
      return upload.uuid
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
