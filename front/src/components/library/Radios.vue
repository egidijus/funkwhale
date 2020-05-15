<template>
  <main v-title="labels.title">
    <section class="ui vertical stripe segment">
      <h2 class="ui header">
        <translate translate-context="Content/Radio/Title">Browsing radios</translate>
      </h2>
      <div class="ui hidden divider"></div>
      <div class="ui row">
        <h3 class="ui header">
          <translate translate-context="Content/Radio/Title">Instance radios</translate>
        </h3>
        <div class="ui cards">
          <radio-card v-if="isAuthenticated" :type="'actor_content'" :object-id="$store.state.auth.fullUsername"></radio-card>
          <radio-card v-if="isAuthenticated && hasFavorites" :type="'favorites'"></radio-card>
          <radio-card :type="'random'"></radio-card>
          <radio-card v-if="$store.state.auth.authenticated" :type="'less-listened'"></radio-card>
        </div>
      </div>

      <div class="ui hidden divider"></div>
      <h3 class="ui header">
        <translate translate-context="Content/Radio/Title">User radios</translate>
      </h3>
      <router-link class="ui success basic button" to="/library/radios/build" exact>
        <translate translate-context="Content/Radio/Button.Label/Verb">Create your own radio</translate>
      </router-link>
      <div class="ui hidden divider"></div>
      <div :class="['ui', {'loading': isLoading}, 'form']">
        <div class="fields">
          <div class="field">
            <label><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
            <input name="search" type="text" v-model="query" :placeholder="labels.searchPlaceholder"/>
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
            <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Order</translate></label>
            <select class="ui dropdown" v-model="orderingDirection">
              <option value="+">
                <translate translate-context="Content/Search/Dropdown">Ascending</translate>
              </option>
              <option value="-">
                <translate translate-context="Content/Search/Dropdown">Descending</translate>
              </option>
            </select>
          </div>
          <div class="field">
            <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Results per page</translate></label>
            <select class="ui dropdown" v-model="paginateBy">
              <option :value="parseInt(12)">12</option>
              <option :value="parseInt(25)">25</option>
              <option :value="parseInt(50)">50</option>
            </select>
          </div>
        </div>
      </div>
      <div class="ui hidden divider"></div>
      <div v-if="result && !result.results.length > 0" class="ui placeholder segment">
        <div class="ui icon header">
          <i class="feed icon"></i>
          <translate translate-context="Content/Radios/Placeholder">
            No results matching your query
          </translate>
        </div>
        <router-link
        v-if="$store.state.auth.authenticated"
        :to="{name: 'library.radios.build'}"
        class="ui success button labeled icon">
          <i class="rss icon"></i>
          <translate translate-context="Content/*/Verb">
            Create a radio
          </translate>
        </router-link>
      </div>
      <div
        v-if="result && result.results.length > 0"
        class="ui cards">
        <radio-card
          type="custom"
          v-for="radio in result.results"
          :key="radio.id"
          :custom-radio="radio"></radio-card>
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
import axios from "axios"
import _ from "@/lodash"
import $ from "jquery"

import logger from "@/logging"

import OrderingMixin from "@/components/mixins/Ordering"
import PaginationMixin from "@/components/mixins/Pagination"
import TranslationsMixin from "@/components/mixins/Translations"
import RadioCard from "@/components/radios/Card"
import Pagination from "@/components/Pagination"

const FETCH_URL = "radios/radios/"

export default {
  mixins: [OrderingMixin, PaginationMixin, TranslationsMixin],
  props: {
    defaultQuery: { type: String, required: false, default: "" },
    scope: { type: String, required: false, default: "all" },
  },
  components: {
    RadioCard,
    Pagination
  },
  data() {
    return {
      isLoading: true,
      result: null,
      page: parseInt(this.defaultPage),
      query: this.defaultQuery,
      orderingOptions: [["creation_date", "creation_date"], ["name", "name"]]
    }
  },
  created() {
    this.fetchData()
  },
  mounted() {
    $(".ui.dropdown").dropdown()
  },
  computed: {
    labels() {
      let searchPlaceholder = this.$pgettext('Content/Search/Input.Placeholder', "Enter a radio name…")
      let title = this.$pgettext('*/*/*', "Radios")
      return {
        searchPlaceholder,
        title
      }
    },
    isAuthenticated () {
      return this.$store.state.auth.authenticated
    },
    hasFavorites () {
      return this.$store.state.favorites.count > 0
    },
  },
  methods: {
    updateQueryString: _.debounce(function() {
      history.pushState(
        {},
        null,
        this.$route.path + '?' + new URLSearchParams(
          {
          query: this.query,
          page: this.page,
          paginateBy: this.paginateBy,
          ordering: this.getOrderingAsString()
        }).toString()
      )
    }, 500),
    fetchData: _.debounce(function() {
      var self = this
      this.isLoading = true
      let url = FETCH_URL
      let params = {
        scope: this.scope,
        page: this.page,
        page_size: this.paginateBy,
        name__icontains: this.query,
        ordering: this.getOrderingAsString(),
      }
      logger.default.debug("Fetching radios")
      axios.get(url, { params: params }).then(response => {
        self.result = response.data
        self.isLoading = false
      })
    }, 500),
    selectPage: function(page) {
      this.page = page
    }
  },
  watch: {
    page() {
      this.updateQueryString()
      this.fetchData()
    },
    paginateBy() {
      this.updateQueryString()
      this.fetchData()
    },
    ordering() {
      this.updateQueryString()
      this.fetchData()
    },
    orderingDirection() {
      this.updateQueryString()
      this.fetchData()
    },
    query() {
      this.updateQueryString()
      this.fetchData()
    }
  }
}
</script>
