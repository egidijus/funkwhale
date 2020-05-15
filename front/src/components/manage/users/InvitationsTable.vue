<template>
  <div>
    <div class="ui inline form">
      <div class="fields">
        <div class="ui field">
          <label><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
          <input name="search" type="text" v-model="search" :placeholder="labels.searchPlaceholder" />
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
          <label><translate translate-context="*/*/*">Status</translate></label>
          <select class="ui dropdown" v-model="isOpen">
            <option :value="null"><translate translate-context="Content/*/Dropdown">All</translate></option>
            <option :value="true"><translate translate-context="Content/Admin/Dropdown/Adjective">Open</translate></option>
            <option :value="false"><translate translate-context="Content/Admin/Dropdown/Adjective">Expired/used</translate></option>
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
        :action-url="'manage/users/invitations/action/'"
        :filters="actionFilters">
        <template slot="header-cells">
          <th><translate translate-context="*/*/*">Owner</translate></th>
          <th><translate translate-context="*/*/*">Status</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Creation date</translate></th>
          <th><translate translate-context="Content/Admin/Table.Label/Noun">Expiration date</translate></th>
          <th><translate translate-context="Content/Admin/Table.Label/Noun">Code</translate></th>
        </template>
        <template slot="row-cells" slot-scope="scope">
          <td>
            <router-link :to="{name: 'manage.users.users.detail', params: {id: scope.obj.id }}">{{ scope.obj.owner.username }}</router-link>
          </td>
          <td>
            <span v-if="scope.obj.users.length > 0" class="ui success basic label"><translate translate-context="Content/Admin/Table">Used</translate></span>
            <span v-else-if="moment().isAfter(scope.obj.expiration_date)" class="ui danger basic label"><translate translate-context="Content/Admin/Table">Expired</translate></span>
            <span v-else class="ui basic label"><translate translate-context="Content/Admin/Table">Not used</translate></span>
          </td>
          <td>
            <human-date :date="scope.obj.creation_date"></human-date>
          </td>
          <td>
            <human-date :date="scope.obj.expiration_date"></human-date>
          </td>
          <td>
            {{ scope.obj.code.toUpperCase() }}
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
import moment from 'moment'
import _ from '@/lodash'
import Pagination from '@/components/Pagination'
import ActionTable from '@/components/common/ActionTable'
import OrderingMixin from '@/components/mixins/Ordering'
import TranslationsMixin from '@/components/mixins/Translations'

export default {
  mixins: [OrderingMixin, TranslationsMixin],
  props: {
    filters: {type: Object, required: false}
  },
  components: {
    Pagination,
    ActionTable
  },
  data () {
    let defaultOrdering = this.getOrderingFromString(this.defaultOrdering || '-creation_date')
    return {
      moment,
      isLoading: false,
      result: null,
      page: 1,
      paginateBy: 50,
      search: '',
      isOpen: null,
      orderingDirection: defaultOrdering.direction || '+',
      ordering: defaultOrdering.field,
      orderingOptions: [
        ['expiration_date', 'expiration_date'],
        ['creation_date', 'creation_date']
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
        'q': this.search,
        'is_open': this.isOpen,
        'ordering': this.getOrderingAsString()
      }, this.filters)
      let self = this
      self.isLoading = true
      self.checked = []
      axios.get('/manage/users/invitations/', {params: params}).then((response) => {
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
        searchPlaceholder: this.$pgettext('Content/Admin/Input.Placeholder/Verb', 'Search by username, e-mail address, code…')
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
      let deleteLabel = this.$pgettext('*/*/*/Verb', 'Delete')
      return [
        {
          name: 'delete',
          label: deleteLabel,
          filterCheckable: (obj) => {
            return obj.users.length === 0 && moment().isBefore(obj.expiration_date)
          }
        }
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
      this.page = 1
      this.fetchData()
    },
    isOpen () {
      this.page = 1
      this.fetchData()
    },
    orderingDirection () {
      this.page = 1
      this.fetchData()
    }
  }
}
</script>
