<template>
  <main v-title="labels.reports">
    <section class="ui vertical stripe segment">
      <h2 class="ui header"><translate translate-context="*/Moderation/*/Noun">Reports</translate></h2>
      <div class="ui hidden divider"></div>
      <div class="ui inline form">
        <div class="fields">
          <div class="ui field">
            <label><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
            <form @submit.prevent="search.query = $refs.search.value">
              <input name="search" ref="search" type="text" :value="search.query" :placeholder="labels.searchPlaceholder" />
            </form>
          </div>
          <div class="field">
            <label><translate translate-context="*/*/*">Status</translate></label>
            <select class="ui dropdown" @change="addSearchToken('resolved', $event.target.value)" :value="getTokenValue('resolved', '')">
              <option value="">
                <translate translate-context="Content/*/Dropdown">All</translate>
              </option>
              <option value="yes">
                <translate translate-context="Content/*/*/Short">Resolved</translate>
              </option>
              <option value="no">
                <translate translate-context="Content/*/*/Short">Unresolved</translate>
              </option>
            </select>
          </div>
          <report-category-dropdown
            class="field"
            @input="addSearchToken('category', $event)"
            :all="true"
            :label="true"
            :value="getTokenValue('category', '')"></report-category-dropdown>
          <div class="field">
            <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering</translate></label>
            <select class="ui dropdown" v-model="ordering">
              <option v-for="option in orderingOptions" :value="option[0]">
                {{ sharedLabels.filters[option[1]] }}
              </option>
            </select>
          </div>
          <div class="field">
            <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Order</translate></label>
            <select class="ui dropdown" v-model="orderingDirection">
              <option value="+"><translate translate-context="Content/Search/Dropdown">Ascending</translate></option>
              <option value="-"><translate translate-context="Content/Search/Dropdown">Descending</translate></option>
            </select>
          </div>
        </div>
      </div>
      <div v-if="isLoading" class="ui active inverted dimmer">
        <div class="ui loader"></div>
      </div>
      <div v-else-if="!result || result.count === 0">
        <empty-state @refresh="fetchData()" :refresh="true"></empty-state>
      </div>
      <div v-else-if="mode === 'card'">
        <report-card @handled="fetchData" :obj="obj" v-for="obj in result.results" :key="obj.uuid" />
      </div>
      <div class="ui center aligned basic segment">
        <pagination
          v-if="result && result.count > paginateBy"
          @page-changed="selectPage"
          :current="page"
          :paginate-by="paginateBy"
          :total="result.count"
          ></pagination>
      </div>
    </section>
  </main>
</template>

<script>


import axios from 'axios'
import _ from '@/lodash'
import time from '@/utils/time'
import Pagination from '@/components/Pagination'
import OrderingMixin from '@/components/mixins/Ordering'
import TranslationsMixin from '@/components/mixins/Translations'
import ReportCard from '@/components/manage/moderation/ReportCard'
import ReportCategoryDropdown from '@/components/moderation/ReportCategoryDropdown'
import {normalizeQuery, parseTokens} from '@/search'
import SmartSearchMixin from '@/components/mixins/SmartSearch'


export default {
  mixins: [OrderingMixin, TranslationsMixin, SmartSearchMixin],
  components: {
    Pagination,
    ReportCard,
    ReportCategoryDropdown,
  },
  props: {
    mode: {default: 'card'},
  },
  data () {
    let defaultOrdering = this.getOrderingFromString(this.defaultOrdering || '-creation_date')
    return {
      time,
      isLoading: false,
      result: null,
      page: 1,
      paginateBy: 25,
      search: {
        query: this.defaultQuery,
        tokens: parseTokens(normalizeQuery(this.defaultQuery))
      },
      orderingDirection: defaultOrdering.direction || '+',
      ordering: defaultOrdering.field,
      orderingOptions: [
        ['creation_date', 'creation_date'],
        ['applied_date', 'applied_date'],
      ],
      targets: {
        track: {}
      }
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
      this.result = null
      axios.get('manage/moderation/reports/', {params: params}).then((response) => {
        self.result = response.data
        self.isLoading = false
        if (self.search.query === 'resolved:no') {
          console.log('Refreshing sidebar notifications')
          self.$store.commit('ui/incrementNotifications', {type: 'pendingReviewReports', value: response.data.count})
        }
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    fetchTargets () {
      // we request target data via the API so we can display previous state
      // additionnal data next to the edit card
      let self = this
      let typesAndIds = {
        track: {
          url: 'tracks/',
          ids: [],
        }
      }
      this.result.results.forEach((m) => {
        if (!m.target || !typesAndIds[m.target.type]) {
          return
        }
        typesAndIds[m.target.type]['ids'].push(m.target.id)
      })
      Object.keys(typesAndIds).forEach((k) => {
        let config = typesAndIds[k]
        if (config.ids.length === 0) {
          return
        }
        axios.get(config.url, {params: {id: _.uniq(config.ids), hidden: 'null'}}).then((response) => {
          response.data.results.forEach((e) => {
            self.$set(self.targets[k], e.id, {
              payload: e,
              currentState: edits.getCurrentStateForObj(e, edits.getConfigs.bind(self)()[k])
            })
          })
        }, error => {
          self.errors = error.backendErrors
        })
      })
    },
    selectPage: function (page) {
      this.page = page
    },
    handle (type, id, value) {
      if (type === 'delete') {
        this.exclude.push(id)
      }

      this.result.results.forEach((e) => {
        if (e.uuid === id) {
          e.is_approved = value
        }
      })
    },
    getCurrentState (target) {
      if (!target) {
        return {}
      }
      if (this.targets[target.type] && this.targets[target.type][String(target.id)]) {
        return this.targets[target.type][String(target.id)].currentState
      }
      return {}
    }
  },
  computed: {
    labels () {
      return {
        searchPlaceholder: this.$pgettext('Content/Search/Input.Placeholder', 'Search by account, summary, domain…'),
        reports: this.$pgettext('*/Moderation/*/Noun', "Reports"),
      }
    },
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
