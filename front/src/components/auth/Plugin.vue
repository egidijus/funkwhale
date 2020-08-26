<template>
  <form :class="['ui segment form', {loading: isLoading}]" @submit.prevent="submit">  
    <h3>{{ plugin.label }}</h3>
    <div v-if="plugin.description" v-html="markdown.makeHtml(plugin.description)"></div>
    <template v-if="plugin.homepage" >
      <div class="ui small hidden divider"></div>
      <a :href="plugin.homepage" target="_blank">
        <i class="external icon"></i>
        <translate translate-context="Footer/*/List item.Link/Short, Noun">Documentation</translate>
      </a>
    </template>
    <div class="ui clearing hidden divider"></div> 
    <div v-if="errors.length > 0" role="alert" class="ui negative message">
      <h4 class="header"><translate translate-context="Content/*/Error message.Title">Error while saving plugin</translate></h4>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <div class="field">
      <div class="ui toggle checkbox">
        <input :id="`${plugin.name}-enabled`" type="checkbox" v-model="enabled" />
        <label :for="`${plugin.name}-enabled`"><translate translate-context="*/*/*">Enabled</translate></label>
      </div>
    </div>
    <div class="ui clearing hidden divider"></div> 
    <div v-if="plugin.source" class="field">
      <label for="plugin-library"><translate translate-context="*/*/*/Noun">Library</translate></label>
      <select id="plugin-library" v-model="values['library']">
        <option :value="l.uuid" v-for="l in libraries" :key="l.uuid">{{ l.name }}</option>
      </select>
      <div>
        <translate translate-context="*/*/Paragraph/Noun">Library where files should be imported.</translate>
      </div>
    </div>
    <template v-if="plugin.conf && plugin.conf.length > 0" v-for="field in plugin.conf">
      <div v-if="field.type === 'text'" class="field">
        <label :for="`plugin-${field.name}`">{{ field.label || field.name }}</label>
        <input :id="`plugin-${field.name}`" type="text" v-model="values[field.name]">
        <div v-if="field.help" v-html="markdown.makeHtml(field.help)"></div>
      </div>
      <div v-if="field.type === 'long_text'" class="field">
        <label :for="`plugin-${field.name}`">{{ field.label || field.name }}</label>
        <textarea :id="`plugin-${field.name}`" type="text" v-model="values[field.name]" rows="5" />
        <div v-if="field.help" v-html="markdown.makeHtml(field.help)"></div>
      </div>
      <div v-if="field.type === 'url'" class="field">
        <label :for="`plugin-${field.name}`">{{ field.label || field.name }}</label>
        <input :id="`plugin-${field.name}`" type="url" v-model="values[field.name]">
        <div v-if="field.help" v-html="markdown.makeHtml(field.help)"></div>
      </div>
      </div>
      <div v-if="field.type === 'password'" class="field">
        <label :for="`plugin-${field.name}`">{{ field.label || field.name }}</label>
        <input :id="`plugin-${field.name}`" type="password" v-model="values[field.name]">
        <div v-if="field.help" v-html="markdown.makeHtml(field.help)"></div>
      </div>
    </template>
    <button
      type="submit"
      :class="['ui', {'loading': isLoading}, 'right', 'floated', 'button']">
        <translate translate-context="Content/*/Button.Label/Verb">Save</translate>
    </button>
    <button
      type="scan"
      v-if="plugin.source"
      @click.prevent="submitAndScan"
      :class="['ui', {'loading': isLoading}, 'right', 'floated', 'button']">
        <translate translate-context="Content/*/Button.Label/Verb">Scan</translate>
    </button>
    <div class="ui clearing hidden divider"></div> 
  </form>
</template>

<script>
import axios from "axios"
import lodash from '@/lodash'
import showdown from 'showdown'
export default {
  props: ['plugin', "libraries"],
  data () {
    return {
      markdown: new showdown.Converter(),
      isLoading: false,
      enabled: this.plugin.enabled,
      values: lodash.clone(this.plugin.values || {}),
      errors: [],
    }
  },
  methods: {
    async submit () {
      this.isLoading = true
      this.errors = []
      let url = `plugins/${this.plugin.name}`
      let enableUrl = this.enabled ? `${url}/enable` : `${url}/enable`
      await axios.post(enableUrl)
      try {
        await axios.post(url, this.values)
      } catch (e) {
        this.errors = e.backendErrors
      }
      this.isLoading = false
    },
    async scan () {
      this.isLoading = true
        this.errors = []
        let url = `plugins/${this.plugin.name}/scan`
        try {
          await axios.post(url, this.values)
        } catch (e) {
          this.errors = e.backendErrors
        }
        this.isLoading = false
    },
    async submitAndScan () {
      await this.submit()
      await this.scan()
    }
  },
}
</script>
