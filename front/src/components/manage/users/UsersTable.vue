<template>
  <div>
    <div class="ui inline form">
      <div class="fields">
        <div class="ui field">
          <label for="users-search"><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
          <input id="users-search" name="search" type="text" v-model="search" :placeholder="labels.searchPlaceholder" />
        </div>
        <div class="field">
          <label for="users-ordering"><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering</translate></label>
          <select id="users-ordering" class="ui dropdown" v-model="ordering">
            <option v-for="option in orderingOptions" :value="option[0]">
              {{ sharedLabels.filters[option[1]] }}
            </option>
          </select>
        </div>
        <div class="field">
          <label for="users-ordering-direction"><translate translate-context="Content/Search/Dropdown.Label/Noun">Order</translate></label>
          <select id="users-ordering-direction" class="ui dropdown" v-model="orderingDirection">
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
        :action-url="'manage/library/uploads/action/'"
        :filters="actionFilters">
        <template slot="header-cells">
          <th><translate translate-context="Content/*/*">Username</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Email</translate></th>
          <th><translate translate-context="Content/Admin/Table.Label/Short, Noun">Account status</translate></th>
          <th><translate translate-context="Content/Admin/Table.Label/Short, Noun (Value is a date)">Sign-up</translate></th>
          <th><translate translate-context="Content/Profile/Table.Label/Short, Noun (Value is a date)">Last activity</translate></th>
          <th><translate translate-context="Content/*/*/Noun">Permissions</translate></th>
          <th><translate translate-context="*/*/*">Status</translate></th>
        </template>
        <template slot="row-cells" slot-scope="scope">
          <td>
            <router-link v-if="scope.obj.actor" :to="{name: 'manage.moderation.accounts.detail', params: {id: scope.obj.actor.full_username }}">{{ scope.obj.username }}</router-link>
            <router-link v-else :to="{name: 'manage.moderation.accounts.detail', params: {id: scope.obj.full_username }}">{{ scope.obj.username }}</router-link>
          </td>
          <td>
            <span>{{ scope.obj.email }}</span>
          </td>
          <td>
            <span v-if="scope.obj.is_active" class="ui basic success label"><translate translate-context="Content/Admin/Table">Active</translate></span>
            <span v-else class="ui basic label"><translate translate-context="Content/Admin/Table">Inactive</translate></span>
          </td>
          <td>
            <human-date :date="scope.obj.date_joined"></human-date>
          </td>
          <td>
            <human-date v-if="scope.obj.last_activity" :date="scope.obj.last_activity"></human-date>
            <template v-else><translate translate-context="*/*/*">N/A</translate></template>
          </td>
          <td>
            <template v-for="p in permissions">
              <span class="ui basic tiny label" v-if="scope.obj.permissions[p.code]">{{ p.label }}</span>
            </template>
          </td>
          <td>
            <span v-if="scope.obj.is_superuser" class="ui pink label"><translate translate-context="Content/Admin/Table.User role">Admin</translate></span>
            <span v-else-if="scope.obj.is_staff" class="ui purple label"><translate translate-context="Content/Profile/User role">Staff member</translate></span>
            <span v-else class="ui basic label"><translate translate-context="Content/Admin/Table, User role">Regular user</translate></span>
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
    let defaultOrdering = this.getOrderingFromString(this.defaultOrdering || '-date_joined')
    return {
      time,
      isLoading: false,
      result: null,
      page: 1,
      paginateBy: 50,
      search: '',
      orderingDirection: defaultOrdering.direction || '+',
      ordering: defaultOrdering.field,
      orderingOptions: [
        ['date_joined', 'date_joined'],
        ['last_activity', 'last_activity'],
        ['username', 'username']
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
        'ordering': this.getOrderingAsString()
      }, this.filters)
      let self = this
      self.isLoading = true
      self.checked = []
      axios.get('/manage/users/users/', {params: params}).then((response) => {
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
        searchPlaceholder: this.$pgettext('Content/Search/Input.Placeholder', 'Search by username, e-mail address, name…')
      }
    },
    privacyLevels () {
      return {}
    },
    permissions () {
      return [
        {
          'code': 'library',
          'label': this.$pgettext('*/*/*/Noun', 'Library')
        },
        {
          'code': 'moderation',
          'label': this.$pgettext('*/Moderation/*', 'Moderation')
        },
        {
          'code': 'settings',
          'label': this.$pgettext('*/*/*/Noun', 'Settings')
        }
      ]
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
        // {
        //   name: 'delete',
        //   label: this.$pgettext('Content/Admin/Button.Label/Verb', 'Delete'),
        //   isDangerous: true
        // }
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
