<template>
  <div class="ui text container">
    <slot></slot>
    <div class="ui inline form">
      <div class="fields">
        <div class="ui field">
          <label for="search-edits"><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
          <form @submit.prevent="search.query = $refs.search.value">
            <input id="search-edits" name="search" ref="search" type="text" :value="search.query" :placeholder="labels.searchPlaceholder" />
          </form>
        </div>
        <div class="field">
          <label for="edit-status"><translate translate-context="*/*/*">Status</translate></label>
          <select id="edit-status" class="ui dropdown" @change="addSearchToken('is_approved', $event.target.value)" :value="getTokenValue('is_approved', '')">
            <option value="">
              <translate translate-context="Content/*/Dropdown">All</translate>
            </option>
            <option value="null">
              <translate translate-context="Content/Admin/*/Noun">Pending review</translate>
            </option>
            <option value="yes">
              <translate translate-context="Content/*/*/Short">Approved</translate>
            </option>
            <option value="no">
              <translate translate-context="Content/Library/*/Short">Rejected</translate>
            </option>
          </select>
        </div>
        <div class="field">
          <label for="edit-ordering"><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering</translate></label>
          <select id="edit-ordering" class="ui dropdown" v-model="ordering">
            <option v-for="option in orderingOptions" :value="option[0]">
              {{ sharedLabels.filters[option[1]] }}
            </option>
          </select>
        </div>
        <div class="field">
          <label for="edit-ordering-direction"><translate translate-context="Content/Search/Dropdown.Label/Noun">Order</translate></label>
          <select id="edit-ordering-direction" class="ui dropdown" v-model="orderingDirection">
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
      <div v-else-if="result && result.count > 0">
        <edit-card
          :obj="obj"
          :current-state="getCurrentState(obj.target)"
          v-for="obj in result.results"
          @deleted="handle('delete', obj.uuid, null)"
          @approved="handle('approved', obj.uuid, $event)"
          :key="obj.uuid" />
      </div>
      <empty-state v-else :refresh="true" @refresh="fetchData()"></empty-state>
    </div>
    <div class="ui hidden divider"></div>
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
import OrderingMixin from '@/components/mixins/Ordering'
import TranslationsMixin from '@/components/mixins/Translations'
import EditCard from '@/components/library/EditCard'
import {normalizeQuery, parseTokens} from '@/search'
import SmartSearchMixin from '@/components/mixins/SmartSearch'

import edits from '@/edits'


export default {
  mixins: [OrderingMixin, TranslationsMixin, SmartSearchMixin],
  props: {
    filters: {type: Object, required: false}
  },
  components: {
    Pagination,
    EditCard
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
      axios.get('mutations/', {params: params}).then((response) => {
        self.result = response.data
        self.isLoading = false
        self.fetchTargets()
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
        searchPlaceholder: this.$pgettext('Content/Search/Input.Placeholder', 'Search by account, summary, domain…')
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
