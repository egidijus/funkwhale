<template>
  <div>

    <div class="ui top attached tabular menu">
      <button :class="[{active: !isPreviewing}, 'item']" @click.stop.prevent="isPreviewing = false">
        <translate translate-context="Content/*/Button.Label/Verb">Edit form</translate>
      </button>
      <button :class="[{active: isPreviewing}, 'item']" @click.stop.prevent="isPreviewing = true">
        <translate translate-context="*/Form/Menu.item">Preview form</translate>
      </button>
    </div>
    <div v-if="isPreviewing" class="ui bottom attached segment">
      <signup-form
        :customization="local"
        :signup-approval-enabled="signupApprovalEnabled"
        :fetch-description-html="true"></signup-form>
      <div class="ui clearing hidden divider"></div>
    </div>
    <div v-else class="ui bottom attached segment">
      <div class="field">
        <label for="help-text">
          <translate translate-context="*/*/Label">Help text</translate>
        </label>
        <p>
          <translate translate-context="*/*/Help">An optional text to be displayed at the start of the sign-up form.</translate>
        </p>
        <content-form
          field-id="help-text"
          :permissive="true"
          :value="(local.help_text || {}).text"
          @input="update('help_text.text', $event)"></content-form>
      </div>
      <div class="field">
        <label>
          <translate translate-context="*/*/Label">Additional fields</translate>
        </label>
        <p>
          <translate translate-context="*/*/Help">Additional form fields to be displayed in the form. Only shown if manual sign-up validation is enabled.</translate>
        </p>
        <table v-if="local.fields.length > 0">
          <thead>
            <tr>
              <th>
                <translate translate-context="*/*/Form-builder,Help">Field label</translate>
              </th>
              <th>
                <translate translate-context="*/*/Form-builder,Help">Field type</translate>
              </th>
              <th>
                <translate translate-context="*/*/Form-builder,Help">Required</translate>
              </th>
              <th><span class="visually-hidden"><translate translate-context="*/*/Form-builder,Help">Actions</translate></span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(field, idx) in local.fields">
              <td>
                <input type="text" v-model="field.label" required>
              </td>
              <td>
                <select v-model="field.input_type">
                  <option value="short_text">
                    <translate translate-context="*/*/Form-builder">Short text</translate>
                  </option>
                  <option value="long_text">
                    <translate translate-context="*/*/Form-builder">Long text</translate>
                  </option>
                </select>
              </td>
              <td>
                <select v-model="field.required">
                  <option :value="true">
                    <translate translate-context="*/*/*">Yes</translate>
                  </option>
                  <option :value="false">
                    <translate translate-context="*/*/*">No</translate>
                  </option>
                </select>
              </td>
              <td>
                <i
                  :disabled="idx === 0"
                  @click="move(idx, -1)" rel="button"
                  :title="labels.up"
                  :class="['up', 'arrow', {disabled: idx === 0}, 'icon']"></i>
                <i
                  :disabled="idx >= local.fields.length - 1"
                  @click="move(idx, 1)" rel="button"
                  :title="labels.down"
                  :class="['down', 'arrow', {disabled: idx >= local.fields.length - 1}, 'icon']"></i>
                <i @click="remove(idx)" rel="button" :title="labels.delete" class="x icon"></i>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="ui hidden divider"></div>
        <button v-if="local.fields.length < maxFields" class="ui basic button" @click.stop.prevent="addField">
          <translate translate-context="*/*/Form-builder">Add a new field</translate>
        </button>
      </div>
    </div>
    <div class="ui hidden divider"></div>
  </div>
</template>

<script>
import lodash from '@/lodash'

import SignupForm from "@/components/auth/SignupForm"

function arrayMove(arr, oldIndex, newIndex) {
  if (newIndex >= arr.length) {
    var k = newIndex - arr.length + 1
    while (k--) {
      arr.push(undefined)
    }
  }
  arr.splice(newIndex, 0, arr.splice(oldIndex, 1)[0])
  return arr
};

// v-model with objects is complex, cf
// https://simonkollross.de/posts/vuejs-using-v-model-with-objects-for-custom-components
export default {
  props: {
    value: {type: Object},
    signupApprovalEnabled: {type: Boolean},
  },
  components: {
    SignupForm
  },
  data () {
    return {
      maxFields: 10,
      isPreviewing: false
    }
  },
  created () {
    this.$emit('input', this.local)
  },
  computed: {
    labels () {
      return {
        delete: this.$pgettext('*/*/*', 'Delete'),
        up: this.$pgettext('*/*/*', 'Move up'),
        down: this.$pgettext('*/*/*', 'Move down'),
      }
    },
    local() {
      return (this.value && this.value.fields) ? this.value : { help_text: {text: null, content_type: "text/markdown"}, fields: [] }
    },
  },
  methods: {
    addField () {
      let newValue = lodash.tap(lodash.cloneDeep(this.local), v => v.fields.push({
        label: this.$pgettext('*/*/Form-builder', 'Additional field') + ' ' + (this.local.fields.length + 1),
        required: true,
        input_type: 'short_text',
      }))
      this.$emit('input', newValue)
    },
    remove (idx) {
      this.$emit('input', lodash.tap(lodash.cloneDeep(this.local), v => v.fields.splice(idx, 1)))
    },
    move (idx, incr) {
      if (idx === 0 && incr < 0) {
        return
      }
      if (idx + incr >= this.local.fields.length) {
        return
      }
      let newFields = arrayMove(lodash.cloneDeep(this.local).fields, idx, idx + incr)
      this.update('fields', newFields)
    },
    update(key, value) {
      if (key === 'help_text.text') {
        key = 'help_text'
        if (!value || value.length === 0) {
          value = null
        } else {
          value = {
            text: value,
            content_type: "text/markdown"
          }
        }
      }
      this.$emit('input', lodash.tap(lodash.cloneDeep(this.local), v => lodash.set(v, key, value)))
    },
  },
}
</script>
