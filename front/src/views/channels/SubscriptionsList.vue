<template>
  <main class="main pusher" v-title="labels.title">
    <section class="ui head vertical stripe segment container">
      <h1 class="ui with-actions header">
        {{ labels.title }}
        <div class="actions">
          <a @click.stop.prevent="showSubscribeModal = true">
            <i class="plus icon"></i>
            <translate translate-context="Content/Profile/Button">Add new</translate>
          </a>
        </div>
      </h1>
      <modal class="tiny" :show.sync="showSubscribeModal" :fullscreen="false">
        <h2 class="header">
          <translate translate-context="*/*/*/Noun">Subscription</translate>
        </h2>
        <div class="scrolling content" ref="modalContent">
          <remote-search-form
            type="both"
            :show-submit="false"
            :standalone="false"
            @subscribed="showSubscribeModal = false; reloadWidget()"
            :redirect="true"></remote-search-form>
        </div>
        <div class="actions">
          <button class="ui basic deny button">
            <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
          </button>
          <button form="remote-search" type="submit" class="ui primary button">
            <i class="bookmark icon"></i>
            <translate translate-context="*/*/*/Verb">Subscribe</translate>
          </button>
        </div>
      </modal>



      <inline-search-bar v-model="query" @search="reloadWidget" :placeholder="labels.searchPlaceholder"></inline-search-bar>
      <channels-widget
        :key="widgetKey"
        :limit="50"
        :show-modification-date="true"
        :filters="{q: query, subscribed: 'true', ordering: '-modification_date'}"></channels-widget>
    </section>
  </main>
</template>

<script>
import axios from "axios"
import Modal from '@/components/semantic/Modal'

import ChannelsWidget from "@/components/audio/ChannelsWidget"
import RemoteSearchForm from "@/components/RemoteSearchForm"

export default {
  props: ["defaultQuery"],
  components: {
    ChannelsWidget,
    RemoteSearchForm,
    Modal,
  },
  data() {
    return {
      query: this.defaultQuery || '',
      channels: [],
      count: 0,
      isLoading: false,
      errors: null,
      previousPage: null,
      nextPage: null,
      widgetKey: String(new Date()),
      showSubscribeModal: false,
    }
  },
  created () {
    this.fetchData()
  },
  computed: {
    labels () {
      return {
        title: this.$pgettext("Content/Subscriptions/Header", "Subscribed Channels"),
        searchPlaceholder: this.$pgettext("Content/Subscriptions/Form.Placeholder", "Filter by name…"),
      }
    },
  },
  methods: {
    fetchData() {
      var self = this
      this.isLoading = true
      axios.get('channels/', {params: {subscribed: "true", q: this.query}}).then(response => {
        self.previousPage = response.data.previous
        self.nextPage = response.data.next
        self.isLoading = false
        self.channels = [...self.channels, ...response.data.results]
        self.count = response.data.count
      })
    },
    reloadWidget () {
      this.widgetKey = String(new Date())
    }
  },
}
</script>
