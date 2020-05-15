<template>
  <tr>
    <td>{{ filter.label }}</td>
    <td>
      <div class="ui toggle checkbox">
        <input name="public" type="checkbox" v-model="exclude" @change="$emit('update-config', index, 'not', exclude)">
        <label></label>
      </div>
    </td>
    <td>
      <div
        v-for="(f, index) in filter.fields"
        class="ui field"
        :key="(f.name, index)"
        :ref="f.name">
        <div :class="['ui', 'search', 'selection', 'dropdown', {'autocomplete': f.autocomplete}, {'multiple': f.type === 'list'}]">
          <i class="dropdown icon"></i>
          <div class="default text">{{ f.placeholder }}</div>
          <input v-if="f.type === 'list' && config[f.name]" :value="config[f.name].join(',')" type="hidden">
          <div v-if="config[f.name]" class="ui menu">
            <div
              v-if="f.type === 'list'"
              v-for="(v, index) in config[f.name]"
              class="ui item"
              :data-value="v">
                <template v-if="config.names">
                  {{ config.names[index] }}
                </template>
                <template v-else>{{ v }}</template>
            </div>
          </div>
        </div>
      </div>
    </td>
    <td>
      <span
        @click="showCandidadesModal = !showCandidadesModal"
        v-if="checkResult"
        :class="['ui', {'success': checkResult.candidates.count > 10}, 'label']">
        {{ checkResult.candidates.count }} tracks matching filter
      </span>
      <modal v-if="checkResult" :show.sync="showCandidadesModal">
        <div class="header">
          <translate translate-context="Popup/Radio/Title/Noun">Tracks matching filter</translate>
        </div>
        <div class="content">
          <div class="description">
            <track-table v-if="checkResult.candidates.count > 0" :tracks="checkResult.candidates.sample"></track-table>
          </div>
        </div>
        <div class="actions">
          <div class="ui basic deny button">
            <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
          </div>
        </div>
      </modal>
    </td>
    <td>
      <button @click="$emit('delete', index)" class="ui basic danger button"><translate translate-context="Content/Radio/Button.Label/Verb">Remove</translate></button>
    </td>
  </tr>
</template>
<script>
import axios from 'axios'
import $ from 'jquery'
import _ from '@/lodash'

import Modal from '@/components/semantic/Modal'
import TrackTable from '@/components/audio/track/Table'
import BuilderFilter from './Filter'

export default {
  components: {
    BuilderFilter,
    TrackTable,
    Modal
  },
  props: {
    filter: {type: Object},
    config: {type: Object},
    index: {type: Number}
  },
  data: function () {
    return {
      checkResult: null,
      showCandidadesModal: false,
      exclude: this.config.not
    }
  },
  mounted: function () {
    let self = this
    this.filter.fields.forEach(f => {
      let selector = ['.dropdown']
      let settings = {
        onChange: function (value, text, $choice) {
          value = $(this).dropdown('get value').split(',')
          if (f.type === 'list' && f.subtype === 'number') {
            value = value.map(e => {
              return parseInt(e)
            })
          }
          self.value = value
          self.$emit('update-config', self.index, f.name, value)
          self.fetchCandidates()
        }
      }
      if (f.type === 'list') {
        selector.push('.multiple')
      }
      if (f.autocomplete) {
        selector.push('.autocomplete')
        settings.fields = f.autocomplete_fields
        settings.minCharacters = 1
        settings.apiSettings = {
          url: self.$store.getters['instance/absoluteUrl'](f.autocomplete + '?' + f.autocomplete_qs),
          beforeXHR: function (xhrObject) {
            xhrObject.setRequestHeader('Authorization', self.$store.getters['auth/header'])
            return xhrObject
          },
          onResponse: function (initialResponse) {
            if (settings.fields.remoteValues) {
              return initialResponse
            }
            return {results: initialResponse.results}
          }
        }
      }
      $(self.$el).find(selector.join('')).dropdown(settings)
    })
  },
  methods: {
    fetchCandidates: function () {
      let self = this
      let url = 'radios/radios/validate/'
      let final = _.clone(this.config)
      final.type = this.filter.type
      final = {'filters': [final]}
      axios.post(url, final).then((response) => {
        self.checkResult = response.data.filters[0]
      })
    }
  },
  watch: {
    exclude: function () {
      this.fetchCandidates()
    }
  }
}
</script>
