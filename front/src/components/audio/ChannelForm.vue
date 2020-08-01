<template>
  <form class="ui form" @submit.prevent.stop="submit">
    <div v-if="errors.length > 0" role="alert" class="ui negative message">
      <h4 class="header"><translate translate-context="Content/*/Error message.Title">Error while saving channel</translate></h4>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <template v-if="metadataChoices">
      <fieldset v-if="creating && step === 1" class="ui grouped channel-type required field">
        <legend>
          <translate translate-context="Content/Channel/Paragraph">What this channel will be used for?</translate>
        </legend>
        <div class="ui hidden divider"></div>
        <div class="field">
          <div :class="['ui', 'radio', 'checkbox', {selected: choice.value == newValues.content_category}]" v-for="choice in categoryChoices">
            <input type="radio" name="channel-category" :id="`category-${choice.value}`" :value="choice.value" v-model="newValues.content_category">
            <label :for="`category-${choice.value}`">
              <span :class="['right floated', 'placeholder', 'image', {circular: choice.value === 'music'}]"></span>
              <strong>{{ choice.label }}</strong>
              <div class="ui small hidden divider"></div>
              {{ choice.helpText }}
            </label>
          </div>
        </div>
      </fieldset>
      <template v-if="!creating || step === 2">
        <div class="ui required field">
          <label for="channel-name">
            <translate translate-context="Content/Channel/*">Name</translate>
          </label>
          <input type="text" required v-model="newValues.name" :placeholder="labels.namePlaceholder">
        </div>
        <div class="ui required field">
          <label for="channel-username">
            <translate translate-context="Content/Channel/*">Social Network Name</translate>
          </label>
          <div class="ui left labeled input">
            <div class="ui basic label">@</div>
            <input type="text" :required="creating" :disabled="!creating" :placeholder="labels.usernamePlaceholder" v-model="newValues.username">
          </div>
          <template v-if="creating">
            <div class="ui small hidden divider"></div>
            <p>
              <translate translate-context="Content/Channels/Paragraph">Used in URLs and to follow this channel on the federation. You cannot change it afterwards.</translate>
            </p>
          </template>
        </div>
        <div class="six wide column">
          <attachment-input
            v-model="newValues.cover"
            :required="false"
            :image-class="newValues.content_category === 'podcast' ? '' : 'circular'"
            @delete="newValues.cover = null">
            <translate translate-context="Content/Channel/*" slot="label">Channel Picture</translate>
          </attachment-input>

        </div>
        <div class="ui small hidden divider"></div>
        <div class="ui stackable grid row">
          <div class="ten wide column">
            <div class="ui field">
              <label for="channel-tags">
                <translate translate-context="*/*/*">Tags</translate>
              </label>
              <tags-selector
                v-model="newValues.tags"
                id="channel-tags"
                :required="false"></tags-selector>
            </div>
          </div>
          <div class="six wide column" v-if="newValues.content_category === 'podcast'">
            <div class="ui required field">
              <label for="channel-language">
                <translate translate-context="*/*/*">Language</translate>
              </label>
              <select
                name="channel-language"
                id="channel-language"
                v-model="newValues.metadata.language"
                required
                class="ui search selection dropdown">
                <option v-for="v in metadataChoices.language" :value="v.value">{{ v.label }}</option>
              </select>
            </div>
          </div>
        </div>
        <div class="ui small hidden divider"></div>
        <div class="ui field">
          <label for="channel-name">
            <translate translate-context="*/*/*">Description</translate>
          </label>
          <content-form v-model="newValues.description"></content-form>
        </div>
        <div class="ui two fields" v-if="newValues.content_category === 'podcast'">
          <div class="ui required field">
            <label for="channel-itunes-category">
              <translate translate-context="*/*/*">Category</translate>
            </label>
            <select
              name="itunes-category"
              id="itunes-category"
              v-model="newValues.metadata.itunes_category"
              required
              class="ui dropdown">
              <option v-for="v in metadataChoices.itunes_category" :value="v.value">{{ v.label }}</option>
            </select>
          </div>
          <div class="ui field">
            <label for="channel-itunes-category">
              <translate translate-context="*/*/*">Subcategory</translate>
            </label>
            <select
              name="itunes-category"
              id="itunes-category"
              v-model="newValues.metadata.itunes_subcategory"
              :disabled="!newValues.metadata.itunes_category"
              class="ui dropdown">
              <option v-for="v in itunesSubcategories" :value="v">{{ v }}</option>
            </select>
          </div>
        </div>
        <div class="ui two fields" v-if="newValues.content_category === 'podcast'">
          <div class="ui field">
            <label for="channel-itunes-email">
              <translate translate-context="*/*/*">Owner email</translate>
            </label>
            <input
              name="channel-itunes-email"
              id="channel-itunes-email"
              type="email"
              v-model="newValues.metadata.owner_email">
          </div>
          <div class="ui field">
            <label for="channel-itunes-name">
              <translate translate-context="*/*/*">Owner name</translate>
            </label>
            <input
              name="channel-itunes-name"
              id="channel-itunes-name"
              maxlength="255"
              v-model="newValues.metadata.owner_name">
          </div>
        </div>
        <p>
          <translate translate-context="*/*/*">Used for the itunes:email and itunes:name field required by certain platforms such as Spotify or iTunes.</translate>
        </p>
      </template>
    </template>
    <div v-else class="ui active inverted dimmer">
      <div class="ui text loader">
        <translate translate-context="*/*/*">Loading</translate>
      </div>
    </div>
  </form>
</template>

<script>
import axios from 'axios'

import AttachmentInput from '@/components/common/AttachmentInput'
import TagsSelector from '@/components/library/TagsSelector'

function slugify(text) {
  return text.toString().toLowerCase()
    .replace(/\s+/g, '')           // Remove spaces
    .replace(/[^\w]+/g, '')        // Remove all non-word chars
}

export default {
  props: {
    object: {type: Object, required: false, default: null},
    step: {type: Number, required: false, default: 1},
  },
  components: {
    AttachmentInput,
    TagsSelector
  },

  created () {
    this.fetchMetadataChoices()
  },
  data () {
    let oldValues = {}
    if (this.object) {
      oldValues.metadata = {...(this.object.metadata || {})}
      oldValues.name = this.object.artist.name
      oldValues.description = this.object.artist.description
      oldValues.cover = this.object.artist.cover
      oldValues.tags = this.object.artist.tags
      oldValues.content_category = this.object.artist.content_category
      oldValues.username = this.object.actor.preferred_username
    }
    return {
      isLoading: false,
      errors: [],
      metadataChoices: null,
      newValues: {
        name: oldValues.name || "",
        username: oldValues.username || "",
        tags: oldValues.tags || [],
        description: (oldValues.description || {}).text || "",
        cover: (oldValues.cover || {}).uuid || null,
        content_category: oldValues.content_category || "podcast",
        metadata: oldValues.metadata || {},
      }
    }
  },
  computed: {
    creating () {
      return this.object === null
    },
    categoryChoices () {
      return [
        {
          value: "podcast",
          label: this.$pgettext('*/*/*', "Podcasts"),
          helpText: this.$pgettext('Content/Channels/Help', "Host your episodes and keep your community updated."),
        },
        {
          value: "music",
          label: this.$pgettext('*/*/*', "Artist discography"),
          helpText: this.$pgettext('Content/Channels/Help', "Publish music you make as a nice discography of albums and singles."),
        }
      ]
    },
    itunesSubcategories () {
      for (let index = 0; index < this.metadataChoices.itunes_category.length; index++) {
        const element = this.metadataChoices.itunes_category[index];
        if (element.value === this.newValues.metadata.itunes_category) {
          return element.children || []
        }
      }
      return []
    },
    labels () {
      return {
        namePlaceholder: this.$pgettext('Content/Channel/Form.Field.Placeholder', "Awesome channel name"),
        usernamePlaceholder: this.$pgettext('Content/Channel/Form.Field.Placeholder', "awesomechannelname"),
      }
    },
    submittable () {
      let v = this.newValues.name && this.newValues.username
      if (this.newValues.content_category === 'podcast') {
        v = v && this.newValues.metadata.itunes_category && this.newValues.metadata.language
      }
      return !!v
    }
  },
  methods: {
    fetchMetadataChoices () {
      let self = this
      axios.get('channels/metadata-choices').then((response) => {
        self.metadataChoices = response.data
      }, error => {
        self.errors = error.backendErrors
      })
    },
    submit () {
      this.isLoading = true
      let self = this
      let handler = this.creating ? axios.post : axios.patch
      let url = this.creating ? `channels/` : `channels/${this.object.uuid}`
      let payload = {
        name: this.newValues.name,
        username: this.newValues.username,
        tags: this.newValues.tags,
        content_category: this.newValues.content_category,
        cover: this.newValues.cover,
        metadata: this.newValues.metadata,
      }
      if (this.newValues.description) {
        payload.description = {
          content_type: 'text/markdown',
          text: this.newValues.description,
        }
      } else {
        payload.description = null
      }

      handler(url, payload).then((response) => {
        self.isLoading = false
        if (self.creating) {
          self.$emit('created', response.data)
        } else {
          self.$emit('updated', response.data)
        }
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
        self.$emit('errored', self.errors)
      })
    }
  },
  watch: {
    "newValues.name" (v) {
      if (this.creating) {
        this.newValues.username = slugify(v)
      }
    },
    "newValues.metadata.itunes_category" (v) {
      this.newValues.metadata.itunes_subcategory = null
    },
    "newValues.content_category": {
      handler (v) {
        this.$emit("category", v)
      },
      immediate: true
    },
    isLoading: {
      handler (v) {
        this.$emit("loading", v)
      },
      immediate: true
    },
    submittable: {
      handler (v) {
        this.$emit("submittable", v)
      },
      immediate: true
    },
  }
}
</script>
