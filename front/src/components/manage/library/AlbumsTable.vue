<template>
  <div>
    <div class="ui inline form">
      <div class="fields">
        <div class="ui six wide field">
          <label for="albums-search"><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
          <form @submit.prevent="search.query = $refs.search.value">
            <input id="albums-search" name="search" ref="search" type="text" :value="search.query" :placeholder="labels.searchPlaceholder" />
          </form>
        </div>
        <div class="field">
          <label for="albums-ordering"><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering</translate></label>
          <select id="albums-ordering" class="ui dropdown" v-model="ordering">
            <option v-for="option in orderingOptions" :value="option[0]">
              {{ sharedLabels.filters[option[1]] }}
            </option>
          </select>
        </div>
        <div class="field">
          <label for="albums-ordering-direction"><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering direction</translate></label>
          <select class="ui dropdown" v-model="orderingDirection">
            <option value="+"><translate translate-context="Content/Search/Dropdown">Ascending</translate></option>
            <option value="-"><translate translate-context="Content/Search/Dropdown">Descending</translate></option>
          </select>
        </div>
      </div>
      </div>
    <div class="dimmable">
      <div v-if="isLoading" class="ui active inverted dimmer">
          <div class="ui loader"></div>
      </div>
      <action-table
        v-if="result"
        @action-launched="fetchData"
        :objects-data="result"
        :actions="actions"
        action-url="manage/library/albums/action/"
        :filters="actionFilters">
        <template slot="header-cells">
          <th><translate translate-context="*/*/*/Noun">Title</translate></th>
          <th><translate translate-context="*/*/*/Noun">Artist</translate></th>
          <th><translate translate-context="Content/Moderation/*/Noun">Domain</translate></th>
          <th><translate translate-context="*/*/*">Tracks</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Release date</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Creation date</translate></th>
        </template>
        <template slot="row-cells" slot-scope="scope">
          <td>
            <router-link :to="{name: 'manage.library.albums.detail', params: {id: scope.obj.id }}">{{ scope.obj.title }}</router-link>
          </td>
          <td>
            <router-link :to="{name: 'manage.library.artists.detail', params: {id: scope.obj.artist.id }}">
              <i class="wrench icon"></i>
              <span class="visually-hidden">{{ labels.openModeration }}</span>
            </router-link>
            <span role="button" class="discrete link" @click="addSearchToken('artist', scope.obj.artist.name)" :title="scope.obj.artist.name">{{ scope.obj.artist.name }}</span>
          </td>
          <td>
            <template v-if="!scope.obj.is_local">
              <router-link :to="{name: 'manage.moderation.domains.detail', params: {id: scope.obj.domain }}">
                <i class="wrench icon"></i>
                <span class="visually-hidden">{{ labels.openModeration }}</span>
              </router-link>
              <span role="button" class="discrete link" @click="addSearchToken('domain', scope.obj.domain)">{{ scope.obj.domain }}</span>
            </template>
            <span role="button" v-else class="ui tiny accent icon link label" @click="addSearchToken('domain', scope.obj.domain)">
              <i class="home icon"></i>
              <translate translate-context="Content/Moderation/*/Short, Noun">Local</translate>
            </span>
          </td>
          <td>
            {{ scope.obj.tracks_count }}
          </td>
          <td>
            <human-date v-if="scope.obj.release_date" :date="scope.obj.release_date"></human-date>
            <translate v-else translate-context="*/*/*">N/A</translate>

          </td>
          <td>
            <human-date :date="scope.obj.creation_date"></human-date>
          </td>
        </template>
      </action-table>
    </div>
    <div>
      <pagination
        v-if="result && result.count > paginateBy"
        @page-changed="selectPage"
        :compact="true"
        :current="page"
        :paginate-by="paginateBy"
        :total="result.count"
        ></pagination>

      <span v-if="result && result.results.length > 0">
        <translate translate-context="Content/*/Paragraph"
          :translate-params="{start: ((page-1) * paginateBy) + 1, end: ((page-1) * paginateBy) + result.results.length, total: result.count}">
          Showing results %{ start }-%{ end } on %{ total }
        </translate>
      </span>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import _ from '@/lodash'
import time from '@/utils/time'
import {normalizeQuery, parseTokens} from '@/search'
import Pagination from '@/components/Pagination'
import ActionTable from '@/components/common/ActionTable'
import OrderingMixin from '@/components/mixins/Ordering'
import TranslationsMixin from '@/components/mixins/Translations'
import SmartSearchMixin from '@/components/mixins/SmartSearch'


export default {
  mixins: [OrderingMixin, TranslationsMixin, SmartSearchMixin],
  props: {
    filters: {type: Object, required: false},
  },
  components: {
    Pagination,
    ActionTable
  },
  data () {
    let defaultOrdering = this.getOrderingFromString(this.defaultOrdering || '-creation_date')
    return {
      time,
      isLoading: false,
      result: null,
      page: 1,
      paginateBy: 50,
      search: {
        query: this.defaultQuery,
        tokens: parseTokens(normalizeQuery(this.defaultQuery))
      },
      orderingDirection: defaultOrdering.direction || '+',
      ordering: defaultOrdering.field,
      orderingOptions: [
        ['creation_date', 'creation_date'],
        ['release_date', 'release_date'],
        ["name", "name"],
      ]
    }
  },
  created () {
    this.fetchData()
  },
  methods: {
    fetchData () {
      let params = _.merge({
        'page': this.page,
        'page_size': this.paginateBy,
        'q': this.search.query,
        'ordering': this.getOrderingAsString()
      }, this.filters)
      let self = this
      self.isLoading = true
      self.checked = []
      axios.get('/manage/library/albums/', {params: params}).then((response) => {
        self.result = response.data
        self.isLoading = false
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    selectPage: function (page) {
      this.page = page
    },
  },
  computed: {
    labels () {
      return {
        searchPlaceholder: this.$pgettext('Content/Search/Input.Placeholder', 'Search by domain, title, artist, MusicBrainz ID…'),
        openModeration: this.$pgettext('Content/Moderation/Verb', 'Open in moderation interface')
      }
    },
    actionFilters () {
      var currentFilters = {
        q: this.search.query
      }
      if (this.filters) {
        return _.merge(currentFilters, this.filters)
      } else {
        return currentFilters
      }
    },
    actions () {
      let deleteLabel = this.$pgettext('*/*/*/Verb', 'Delete')
      let confirmationMessage = this.$pgettext('Popup/*/Paragraph', 'The selected albums will be removed, as well as associated tracks, uploads, favorites and listening history. This action is irreversible.')
      return [
        {
          name: 'delete',
          label: deleteLabel,
          confirmationMessage: confirmationMessage,
          isDangerous: true,
          allowAll: false,
          confirmColor: 'danger',
        },
      ]
    }
  },
  watch: {
    search (newValue) {
      this.page = 1
      this.fetchData()
    },
    page () {
      this.fetchData()
    },
    ordering () {
      this.fetchData()
    },
    orderingDirection () {
      this.fetchData()
    }
  }
}
</script>
