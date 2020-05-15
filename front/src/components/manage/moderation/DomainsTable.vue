<template>
  <div v-if="result.count > 0">
    <div class="ui inline form">
      <div class="fields">
        <div class="ui field">
          <label><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
          <input name="search" type="text" v-model="search" :placeholder="labels.searchPlaceholder" />
        </div>
        <div class="field" v-if="allowListEnabled">
          <label><translate translate-context="Content/Moderation/*/Adjective">Is present on allow-list</translate></label>
          <select class="ui dropdown" v-model="allowed">
            <option :value="null"><translate translate-context="Content/*/Dropdown">All</translate></option>
            <option :value="true"><translate translate-context="*/*/*">Yes</translate></option>
            <option :value="false"><translate translate-context="*/*/*">No</translate></option>
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
    <div class="dimmable">
      <div v-if="isLoading" class="ui active inverted dimmer">
          <div class="ui loader"></div>
      </div>
      <action-table
        v-if="result"
        @action-launched="fetchData"
        :objects-data="result"
        :actions="actions"
        action-url="manage/federation/domains/action/"
        idField="name"
        :filters="actionFilters">
        <template slot="header-cells">
          <th><translate translate-context="*/*/*/Noun">Name</translate></th>
          <th><translate translate-context="*/*/*/Noun">Users</translate></th>
          <th><translate translate-context="Content/Moderation/*/Noun">Received messages</translate></th>
          <th><translate translate-context="Content/Moderation/Table.Label/Short (Value is a date)">First seen</translate></th>
          <th><translate translate-context="Content/Moderation/Table.Label/Short">Under moderation rule</translate></th>
        </template>
        <template slot="row-cells" slot-scope="scope">
          <td>
            <router-link :to="{name: 'manage.moderation.domains.detail', params: {id: scope.obj.name }}">
              {{ scope.obj.name }}
              <i v-if="allowListEnabled && scope.obj.allowed" class="success check icon" :title="labels.allowListTitle"></i>
            </router-link>
          </td>
          <td>
            {{ scope.obj.actors_count }}
          </td>
          <td>
            {{ scope.obj.outbox_activities_count }}
          </td>
          <td>
            <human-date :date="scope.obj.creation_date"></human-date>
          </td>
          <td>
            <span v-if="scope.obj.instance_policy"><i class="shield icon"></i> <translate translate-context="*/*/*">Yes</translate></span>
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
  <div v-else class="ui placeholder segment">
    <div class="ui icon header">
      <i class="server icon"></i>
      <translate translate-context="Content/Home/Placeholder">No interactions with other pods yet</translate>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import _ from '@/lodash'
import time from '@/utils/time'
import Pagination from '@/components/Pagination'
import ActionTable from '@/components/common/ActionTable'
import OrderingMixin from '@/components/mixins/Ordering'
import TranslationsMixin from '@/components/mixins/Translations'

export default {
  mixins: [OrderingMixin, TranslationsMixin],
  props: {
    filters: {type: Object, required: false},
    allowListEnabled: {type: Boolean, default: false},
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
      search: '',
      allowed: null,
      orderingDirection: defaultOrdering.direction || '+',
      ordering: defaultOrdering.field,
      orderingOptions: [
        ['name', 'name'],
        ['creation_date', 'first_seen'],
        ['actors_count', 'users'],
        ['outbox_activities_count', 'received_messages']
      ]

    }
  },
  created () {
    this.fetchData()
  },
  methods: {
    fetchData () {
      let baseFilters = {
        'page': this.page,
        'page_size': this.paginateBy,
        'q': this.search,
        'ordering': this.getOrderingAsString(),
      }
      if (this.allowed !== null) {
        baseFilters.allowed = this.allowed
      }
      let params = _.merge(baseFilters, this.filters)
      let self = this
      self.isLoading = true
      self.checked = []
      axios.get('/manage/federation/domains/', {params: params}).then((response) => {
        self.result = response.data
        self.isLoading = false
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    selectPage: function (page) {
      this.page = page
    }
  },
  computed: {
    labels () {
      return {
        searchPlaceholder: this.$pgettext('Content/Search/Input.Placeholder', 'Search by name…'),
        allowListTitle: this.$pgettext('Content/Moderation/Popup', 'This domain is present in your allow-list'),
      }
    },
    actionFilters () {
      var currentFilters = {
        q: this.search
      }
      if (this.filters) {
        return _.merge(currentFilters, this.filters)
      } else {
        return currentFilters
      }
    },
    actions () {
      return [
        {
          name: 'purge',
          label: this.$pgettext('*/*/*/Verb', 'Purge'),
          isDangerous: true
        },
        {
          name: 'allow_list_add',
          label: this.$pgettext('Content/Moderation/Action/Verb', 'Add to allow-list'),
          filterCheckable: (obj) => {
            return !obj.allowed
          }
        },
        {
          name: 'allow_list_remove',
          label: this.$pgettext('Content/Moderation/Action/Verb', 'Remove from allow-list'),
          filterCheckable: (obj) => {
            return obj.allowed
          }
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
    allowed () {
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
