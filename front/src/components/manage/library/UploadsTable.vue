<template>
  <div>
    <div class="ui inline form">
      <div class="fields">
        <div class="ui six wide field">
          <label><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
          <form @submit.prevent="search.query = $refs.search.value">
            <input name="search" ref="search" type="text" :value="search.query" :placeholder="labels.searchPlaceholder" />
          </form>
        </div>
        <div class="field">
          <label><translate translate-context="*/*/*">Visibility</translate></label>
          <select class="ui dropdown" @change="addSearchToken('privacy_level', $event.target.value)" :value="getTokenValue('privacy_level', '')">
            <option value=""><translate translate-context="Content/*/Dropdown">All</translate></option>
            <option value="me">{{ sharedLabels.fields.privacy_level.shortChoices.me }}</option>
            <option value="instance">{{ sharedLabels.fields.privacy_level.shortChoices.instance }}</option>
            <option value="everyone">{{ sharedLabels.fields.privacy_level.shortChoices.everyone }}</option>
          </select>
        </div>
        <div class="field">
          <label><translate translate-context="Content/*/*/Noun">Import status</translate></label>
          <select class="ui dropdown" @change="addSearchToken('status', $event.target.value)" :value="getTokenValue('status', '')">
            <option value=""><translate translate-context="Content/*/Dropdown">All</translate></option>
            <option value="pending"><translate translate-context="Content/Library/*/Short">Pending</translate></option>
            <option value="skipped"><translate translate-context="Content/Library/*">Skipped</translate></option>
            <option value="errored"><translate translate-context="Content/Library/Dropdown">Failed</translate></option>
            <option value="finished"><translate translate-context="Content/Library/*">Finished</translate></option>
          </select>
        </div>
        <div class="field">
          <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering</translate></label>
          <select class="ui dropdown" v-model="ordering">
            <option v-for="option in orderingOptions" :value="option[0]">
              {{ sharedLabels.filters[option[1]] }}
            </option>
          </select>
        </div>
        <div class="field">
          <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering direction</translate></label>
          <select class="ui dropdown" v-model="orderingDirection">
            <option value="+"><translate translate-context="Content/Search/Dropdown">Ascending</translate></option>
            <option value="-"><translate translate-context="Content/Search/Dropdown">Descending</translate></option>
          </select>
        </div>
      </div>
    </div>
    <import-status-modal :upload="detailedUpload" :show.sync="showUploadDetailModal" />
    <div class="dimmable">
      <div v-if="isLoading" class="ui active inverted dimmer">
          <div class="ui loader"></div>
      </div>
      <action-table
        v-if="result"
        @action-launched="fetchData"
        :objects-data="result"
        :actions="actions"
        action-url="manage/library/uploads/action/"
        :filters="actionFilters">
        <template slot="header-cells">
          <th><translate translate-context="*/*/*/Noun">Name</translate></th>
          <th><translate translate-context="*/*/*/Noun">Library</translate></th>
          <th><translate translate-context="*/*/*/Noun">Account</translate></th>
          <th><translate translate-context="Content/Moderation/*/Noun">Domain</translate></th>
          <th><translate translate-context="*/*/*">Visibility</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Import status</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Size</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Creation date</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Accessed date</translate></th>
        </template>
        <template slot="row-cells" slot-scope="scope">
          <td>
            <router-link :to="{name: 'manage.library.uploads.detail', params: {id: scope.obj.uuid }}" :title="displayName(scope.obj)">
              {{ displayName(scope.obj)|truncate(30, "…", true) }}
            </router-link>
          </td>
          <td>
            <router-link :to="{name: 'manage.library.libraries.detail', params: {id: scope.obj.library.uuid }}">
              <i class="wrench icon"></i>
            </router-link>
            <span role="button" class="discrete link"
              @click="addSearchToken('library_id', scope.obj.library.id)"
              :title="scope.obj.library.name">
              {{ scope.obj.library.name | truncate(20) }}
            </span>
          </td>
          <td>
            <router-link :to="{name: 'manage.moderation.accounts.detail', params: {id: scope.obj.library.actor.full_username }}">
            </router-link>
            <span role="button" class="discrete link" @click="addSearchToken('account', scope.obj.library.actor.full_username)" :title="scope.obj.library.actor.full_username">{{ scope.obj.library.actor.preferred_username }}</span>
          </td>
          <td>
            <template v-if="!scope.obj.is_local">
              <router-link :to="{name: 'manage.moderation.domains.detail', params: {id: scope.obj.domain }}">
                <i class="wrench icon"></i>
              </router-link>
              <span role="button" class="discrete link" @click="addSearchToken('domain', scope.obj.domain)" :title="scope.obj.domain">{{ scope.obj.domain }}</span>
            </template>
            <span role="button" v-else class="ui tiny teal icon link label" @click="addSearchToken('domain', scope.obj.domain)">
              <i class="home icon"></i>
              <translate translate-context="Content/Moderation/*/Short, Noun">Local</translate>
            </span>
          </td>
          <td>
            <span
              role="button"
              class="discrete link"
              @click="addSearchToken('privacy_level', scope.obj.library.privacy_level)"
              :title="sharedLabels.fields.privacy_level.shortChoices[scope.obj.library.privacy_level]">
              {{ sharedLabels.fields.privacy_level.shortChoices[scope.obj.library.privacy_level] }}
            </span>
          </td>
          <td>
            <span class="discrete link" @click="addSearchToken('status', scope.obj.import_status)" :title="sharedLabels.fields.import_status.choices[scope.obj.import_status].help">
              {{ sharedLabels.fields.import_status.choices[scope.obj.import_status].label }}
            </span>
            <button class="ui tiny basic icon button" :title="sharedLabels.fields.import_status.detailTitle" @click="detailedUpload = scope.obj; showUploadDetailModal = true">
              <i class="question circle outline icon"></i>
            </button>
          </td>
          <td>
            <span v-if="scope.obj.size">{{ scope.obj.size | humanSize }}</span>
            <translate v-else translate-context="*/*/*">N/A</translate>
          </td>
          <td>
            <human-date :date="scope.obj.creation_date"></human-date>
          </td>
          <td>
            <human-date v-if="scope.obj.accessed_date" :date="scope.obj.accessed_date"></human-date>
            <translate v-else translate-context="*/*/*">N/A</translate>
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
import ImportStatusModal from '@/components/library/ImportStatusModal'


export default {
  mixins: [OrderingMixin, TranslationsMixin, SmartSearchMixin],
  props: {
    filters: {type: Object, required: false},
  },
  components: {
    Pagination,
    ActionTable,
    ImportStatusModal
  },
  data () {
    let defaultOrdering = this.getOrderingFromString(this.defaultOrdering || '-creation_date')
    return {
      detailedUpload: null,
      showUploadDetailModal: false,
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
        ['modification_date', 'modification_date'],
        ['accessed_date', 'accessed_date'],
        ['size', 'size'],
        ['bitrate', 'bitrate'],
        ['duration', 'duration'],
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
      axios.get('/manage/library/uploads/', {params: params}).then((response) => {
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
    labels () {
      return {
        searchPlaceholder: this.$pgettext('Content/Search/Input.Placeholder', 'Search by domain, actor, name, reference, source…')
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
      let confirmationMessage = this.$pgettext('Popup/*/Paragraph', 'The selected upload will be removed. This action is irreversible.')
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
