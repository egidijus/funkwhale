<template>
  <div ref="dropdown" class="ui multiple search selection dropdown">
    <input type="hidden">
    <i class="dropdown icon"></i>
    <input type="text" class="search">
    <div class="default text">
      <translate translate-context="*/Dropdown/Placeholder/Verb">Search for tags…</translate>
    </div>
  </div>
</template>
<script>
import $ from 'jquery'

import lodash from '@/lodash'
export default {
  props: ['value'],
  mounted () {
    this.$nextTick(() => {
      this.initDropdown()

    })
  },
  methods: {
    initDropdown () {
      let self = this
      let handleUpdate = () => {
        let value = $(self.$refs.dropdown).dropdown('get value').split(',')
        self.$emit('input', value)
        return value
      }
      let settings = {
        keys : {
          delimiter  : 32,
        },
        forceSelection: false,
        saveRemoteData: false,
        filterRemoteData: true,
        preserveHTML : false,
        apiSettings: {
          url: this.$store.getters['instance/absoluteUrl']('/api/v1/tags/?name__startswith={query}&ordering=length&page_size=5'),
          beforeXHR: function (xhrObject) {
            xhrObject.setRequestHeader('Authorization', self.$store.getters['auth/header'])
            return xhrObject
          },
          onResponse(response) {
            let currentSearch = $(self.$refs.dropdown).dropdown('get query')
            response = {
              results: [],
              ...response,
            }
            if (currentSearch) {
              response.results = [{name: currentSearch}, ...response.results]
            }
            return response
          }
        },
        fields: {
          remoteValues: 'results',
          value: 'name'
        },
        allowAdditions: true,
        minCharacters: 1,
        onAdd: handleUpdate,
        onRemove: handleUpdate,
        onLabelRemove: handleUpdate,
        onChange: handleUpdate,
      }
      $(this.$refs.dropdown).dropdown(settings)
      $(this.$refs.dropdown).dropdown('set exactly', this.value)
    }
  },
  watch: {
    value: {
      handler (v) {
        let current = $(this.$refs.dropdown).dropdown('get value').split(',').sort()
        if (!lodash.isEqual([...v].sort(), current)) {
          $(this.$refs.dropdown).dropdown('set exactly', v)
        }
      },
      deep: true
    }
  }
}
</script>
