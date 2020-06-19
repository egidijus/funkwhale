<template>
  <form class="ui form" @submit.prevent="createOrUpdate">
    <h3 class="ui header">
      <translate translate-context="Content/Moderation/Card.Title/Verb" v-if="object" key="1">Edit moderation rule</translate>
      <translate translate-context="Content/Moderation/Card.Button.Label/Verb" v-else key="2">Add a new moderation rule</translate>
    </h3>
    <div v-if="errors && errors.length > 0" role="alert" class="ui negative message">
      <div class="header"><translate translate-context="Content/Moderation/Error message.Title">Error while creating rule</translate></div>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>

    <div class="field" v-if="object">
      <div class="ui toggle checkbox">
        <input id="policy-is-active" v-model="current.isActive" type="checkbox">
        <label for="policy-is-active">
          <translate translate-context="*/*/*/State of feature" v-if="current.isActive" key="1">Enabled</translate>
          <translate translate-context="*/*/*/State of feature" v-else key="2">Disabled</translate>
          <tooltip :content="labels.isActiveHelp" />
        </label>
      </div>
    </div>
    <div class="field">
      <label for="policy-summary">
        <translate translate-context="Content/Moderation/*/Noun">Reason</translate>
        <tooltip :content="labels.summaryHelp" />
      </label>
      <textarea name="policy-summary" id="policy-summary" rows="5" v-model="current.summary"></textarea>
    </div>
    <div class="field">
      <div class="ui toggle checkbox">
        <input id="policy-is-active" v-model="current.blockAll" type="checkbox">
        <label for="policy-is-active">
          <translate translate-context="Content/Moderation/*/Verb">Block everything</translate>
          <tooltip :content="labels.blockAllHelp" />
        </label>
      </div>
    </div>
    <div class="ui horizontal divider">
      <translate translate-context="Content/Moderation/Card.Title">Or customize your rule</translate>
    </div>
    <div v-for="config in fieldConfig" :class="['field']">
      <div class="ui toggle checkbox">
        <input :id="'policy-' + config.id" v-model="current[config.id]" type="checkbox">
        <label :for="'policy-' + config.id">
          <i :class="[config.icon, 'icon']"></i>
          {{ labels[config.id].label }}
          <tooltip :content="labels[config.id].help" />
        </label>
      </div>
    </div>
    <div class="ui hidden divider"></div>
    <button @click.prevent="$emit('cancel')" class="ui basic left floated button">
      <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
    </button>
    <button :class="['ui', 'right', 'floated', 'success', {'disabled loading': isLoading}, 'button']" :disabled="isLoading">
      <translate translate-context="Content/Moderation/Card.Button.Label/Verb" v-if="object" key="1">Update</translate>
      <translate translate-context="Content/Moderation/Card.Button.Label/Verb" v-else key="2">Create</translate>
    </button>
    <dangerous-button v-if="object" class="ui right floated basic danger button" @confirm="remove">
      <translate translate-context="*/*/*/Verb">Delete</translate>
      <p slot="modal-header">
        <translate translate-context="Popup/Moderation/Title">Delete this moderation rule?</translate>
      </p>
      <p slot="modal-content">
        <translate translate-context="Popup/Moderation/Paragraph">This action is irreversible.</translate>
      </p>
      <div slot="modal-confirm">
        <translate translate-context="Popup/Moderation/Button.Label/Verb">Delete moderation rule</translate>
      </div>
    </dangerous-button>
  </form>
</template>

<script>
import axios from 'axios'
import _ from '@/lodash'

export default {
  props: {
    type: {type: String, required: true},
    object: {type: Object, default: null},
    target: {type: String, required: true},
  },
  data () {
    let current = this.object || {}
    return {
      isLoading: false,
      errors: [],
      current: {
        summary: _.get(current, 'summary', ''),
        isActive: _.get(current, 'is_active', true),
        blockAll: _.get(current, 'block_all', true),
        silenceActivity: _.get(current, 'silence_activity', false),
        silenceNotifications: _.get(current, 'silence_notifications', false),
        rejectMedia: _.get(current, 'reject_media', false),
      },
      fieldConfig: [
        // we hide those until we actually have the related features implemented :)
        // {id: "silenceActivity", icon: "feed"},
        // {id: "silenceNotifications", icon: "bell"},
        {id: "rejectMedia", icon: "file"},
      ]
    }
  },
  computed: {
    labels () {
      return {
        summaryHelp: this.$pgettext('Content/Moderation/Help text', "Explain why you're applying this policy. Depending on your instance configuration, this will help you remember why you acted on this account or domain, and may be displayed publicly to help users understand what moderation rules are in place."),
        isActiveHelp: this.$pgettext('Content/Moderation/Help text', "Use this setting to temporarily enable/disable the policy without completely removing it."),
        blockAllHelp: this.$pgettext('Content/Moderation/Help text', "Block everything from this account or domain. This will prevent any interaction with the entity, and purge related content (uploads, libraries, follows, etc.)"),
        silenceActivity: {
          help: this.$pgettext('Content/Moderation/Help text', "Hide account or domain content, except from followers."),
          label: this.$pgettext('Content/Moderation/*/Verb', "Mute activity"),
        },
        silenceNotifications: {
          help: this.$pgettext('Content/Moderation/Help text', "Prevent account or domain from triggering notifications, except from followers."),
          label: this.$pgettext('Content/Moderation/*/Verb', "Mute notifications"),
        },
        rejectMedia: {
          help: this.$pgettext('Content/Moderation/Help text', "Do not download any media file (audio, album cover, account avatar…) from this account or domain. This will purge existing content as well."),
          label: this.$pgettext('Content/Moderation/*/Verb', "Reject media"),
        }
      }
    }
  },
  methods: {
    createOrUpdate () {
      let self = this
      this.isLoading = true
      this.errors = []
      let url, method
      let data = {
        summary: this.current.summary,
        is_active: this.current.isActive,
        block_all: this.current.blockAll,
        silence_activity: this.current.silenceActivity,
        silence_notifications: this.current.silenceNotifications,
        reject_media: this.current.rejectMedia,
        target: {
          type: this.type,
          id: this.target,
        }
      }
      if (this.object) {
        url = `manage/moderation/instance-policies/${this.object.id}/`
        method = 'patch'
      } else {
        url = `manage/moderation/instance-policies/`
        method = 'post'
      }
      axios[method](url, data).then((response) => {
        this.isLoading = false
        self.$emit('save', response.data)
      }, (error) => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    remove () {
      let self = this
      this.isLoading = true
      this.errors = []

      let url = `manage/moderation/instance-policies/${this.object.id}/`
      axios.delete(url).then((response) => {
        this.isLoading = false
        self.$emit('delete')
      }, (error) => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    }
  },
  watch: {
    'current.silenceActivity': function (v) {
      if (v) {
        this.current.blockAll = false
      }
    },
    'current.silenceNotifications': function (v) {
      if (v) {
        this.current.blockAll = false
      }
    },
    'current.rejectMedia': function (v) {
      if (v) {
        this.current.blockAll = false
      }
    },
    'current.blockAll': function (v) {
      if (v) {
        let self = this
        this.fieldConfig.forEach((f) => {
          self.current[f.id] = false
        })
      }
    }
  }
}
</script>
