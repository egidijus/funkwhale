<template>
  <form :id="group.id" class="ui form component-settings-group" @submit.prevent="save">
    <div class="ui divider" />
    <h3 class="ui header">{{ group.label }}</h3>
    <div v-if="errors.length > 0" role="alert" class="ui negative message">
      <h4 class="header"><translate translate-context="Content/*/Error message.Title">Error while saving settings</translate></h4>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <div v-if="result" class="ui positive message">
      <translate translate-context="Content/Settings/Paragraph">Settings updated successfully.</translate>
    </div>
    <p v-if="group.help">{{ group.help }}</p>
    <div v-for="setting in settings" class="ui field">
      <template v-if="setting.field.widget.class !== 'CheckboxInput'">
        <label :for="setting.identifier">{{ setting.verbose_name }}</label>
        <p v-if="setting.help_text">{{ setting.help_text }}</p>
      </template>
      <content-form v-if="setting.fieldType === 'markdown'" v-model="values[setting.identifier]" v-bind="setting.fieldParams" />
      <signup-form-builder
        v-else-if="setting.fieldType === 'formBuilder'"
        :value="values[setting.identifier]"
        :signup-approval-enabled="values.moderation__signup_approval_enabled"
        @input="set(setting.identifier, $event)" />
      <input
        :id="setting.identifier"
        :name="setting.identifier"
        v-else-if="setting.field.widget.class === 'PasswordInput'"
        type="password"
        class="ui input"
        v-model="values[setting.identifier]" />
      <input
        :id="setting.identifier"
        :name="setting.identifier"
        v-else-if="setting.field.widget.class === 'TextInput'"
        type="text"
        class="ui input"
        v-model="values[setting.identifier]" />
      <input
        :id="setting.identifier"
        :name="setting.identifier"
        v-else-if="setting.field.class === 'IntegerField'"
        type="number"
        class="ui input"
        v-model.number="values[setting.identifier]" />
      <textarea
        :id="setting.identifier"
        :name="setting.identifier"
        v-else-if="setting.field.widget.class === 'Textarea'"
        type="text"
        class="ui input"
        v-model="values[setting.identifier]" />
      <div v-else-if="setting.field.widget.class === 'CheckboxInput'" class="ui toggle checkbox">
        <input
          :id="setting.identifier"
          :name="setting.identifier"
          v-model="values[setting.identifier]"
          type="checkbox" />
        <label :for="setting.identifier">{{ setting.verbose_name }}</label>
        <p v-if="setting.help_text">{{ setting.help_text }}</p>
      </div>
      <select
        :id="setting.identifier"
        v-else-if="setting.field.class === 'MultipleChoiceField'"
        v-model="values[setting.identifier]"
        multiple
        class="ui search selection dropdown">
        <option v-for="v in setting.additional_data.choices" :value="v[0]">{{ v[1] }}</option>
      </select>
      <div v-else-if="setting.field.widget.class === 'ImageWidget'">
        <input :id="setting.identifier" type="file" :ref="setting.identifier">
        <div v-if="values[setting.identifier]">
          <div class="ui hidden divider"></div>
          <h3 class="ui header"><translate translate-context="Content/Settings/Title/Noun">Current image</translate></h3>
          <img class="ui image" alt="" v-if="values[setting.identifier]" :src="$store.getters['instance/absoluteUrl'](values[setting.identifier])" />
        </div>
      </div>
    </div>
    <button
      type="submit"
      :class="['ui', {'loading': isLoading}, 'right', 'floated', 'success', 'button']">
        <translate translate-context="Content/*/Button.Label/Verb">Save</translate>
    </button>
  </form>
</template>

<script>
import axios from 'axios'

import lodash from '@/lodash'

export default {
  props: {
    group: {type: Object, required: true},
    settingsData: {type: Array, required: true}
  },
  components: {
    SignupFormBuilder:  () => import(/* webpackChunkName: "signup-form-builder" */ "@/components/admin/SignupFormBuilder"),
  },
  data () {
    return {
      values: {},
      result: null,
      errors: [],
      isLoading: false
    }
  },
  created () {
    let self = this
    this.settings.forEach(e => {
      self.values[e.identifier] = e.value
    })
  },
  methods: {
    save () {
      let self = this
      this.isLoading = true
      self.errors = []
      self.result = null
      let postData = self.values
      let contentType = 'application/json'
      let fileSettingsIDs = this.fileSettings.map((s) => {return s.identifier})
      if (fileSettingsIDs.length > 0) {
        contentType = 'multipart/form-data'
        postData = new FormData()
        this.settings.forEach((s) => {
          if (fileSettingsIDs.indexOf(s.identifier) > -1) {
            let input = self.$refs[s.identifier][0]
            let files = input.files
            console.log('ref', input, files)
            if (files && files.length > 0) {
              postData.append(s.identifier, files[0])
            }
          } else {
            postData.append(s.identifier, self.values[s.identifier])
          }
        })
      }
      axios.post('instance/admin/settings/bulk/', postData, {
        headers: {
          'Content-Type': contentType,
        },
      }).then((response) => {
        self.result = true
        response.data.forEach((s) => {
          self.values[s.identifier] = s.value
        })
        self.isLoading = false
        self.$store.dispatch('instance/fetchSettings')
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    set (key, value) {
      // otherwise reactivity doesn't trigger :/
      this.values = lodash.cloneDeep(this.values)
      this.$set(this.values, key, value)
    }
  },
  computed: {
    settings () {
      let byIdentifier = {}
      this.settingsData.forEach(e => {
        byIdentifier[e.identifier] = e
      })
      return this.group.settings.map(e => {
        return {...byIdentifier[e.name], fieldType: e.fieldType, fieldParams: e.fieldParams || {}}
      })
    },
    fileSettings () {
      return this.settings.filter((s) => {
        return s.field.widget.class === 'ImageWidget'
      })
    }
  }
}
</script>
