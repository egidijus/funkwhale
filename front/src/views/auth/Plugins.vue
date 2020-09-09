<template>
  <main class="main pusher" v-title="labels.title">
    <section class="ui vertical stripe segment">
      <div class="ui small text container">
        <h2>{{ labels.title }}</h2>
        <div v-if="isLoading" class="ui inverted active dimmer">
          <div class="ui loader"></div>
        </div>

        <plugin-form
          v-if="plugins && plugins.length > 0"
          v-for="plugin in plugins"
          :plugin="plugin"
          :libraries="libraries"
          :key="plugin.name"></plugin-form>
        <empty-state v-else></empty-state>
      </div>
    </section>
  </main>
</template>

<script>
import axios from 'axios'
import PluginForm from '@/components/auth/Plugin'

export default {
  components: {
    PluginForm
  },
  data () {
    return {
      isLoading: true,
      plugins: null,
      libraries: null,
    }
  },
  async created () {
    await this.fetchData()
  },
  computed: {
    labels() {
      let title = this.$pgettext('Head/Login/Title', "Manage plugins")
      return {
        title
      }
    }
  },
  methods: {
    async fetchData () {
      this.isLoading = true
      let response = await axios.get('plugins')
      this.plugins = response.data
      response = await axios.get('libraries', {paramis: {scope: 'me', page_size: 50}})
      this.libraries = response.data.results
      this.isLoading = false
    }
  }
}
</script>
