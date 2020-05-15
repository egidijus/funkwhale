<template>
    <div class="ui card">
      <div class="content">
        <div class="header">
          <router-link v-if="radio.id" class="discrete link" :to="{name: 'library.radios.detail', params: {id: radio.id}}">
            {{ radio.name }}
          </router-link>
          <template v-else>
            {{ radio.name }}
          </template>
        </div>
        <div class="description">
          {{ radio.description }}
        </div>
      </div>
      <div class="extra content">
        <user-link v-if="radio.user" :user="radio.user" class="left floated" />
        <div class="ui hidden divider"></div>
        <radio-button class="right floated button" :type="type" :custom-radio-id="customRadioId" :object-id="objectId"></radio-button>
        <router-link
          class="ui basic warning button right floated"
          v-if="$store.state.auth.authenticated && type === 'custom' && radio.user.id === $store.state.auth.profile.id"
          :to="{name: 'library.radios.edit', params: {id: customRadioId }}">
          <translate translate-context="Content/*/Button.Label/Verb">Edit</translate>
        </router-link>
      </div>
    </div>
</template>

<script>
import RadioButton from './Button'

export default {
  props: {
    type: {type: String, required: true},
    customRadio: {required: false},
    objectId: {required: false},
  },
  components: {
    RadioButton
  },
  computed: {
    radio () {
      if (this.customRadio) {
        return this.customRadio
      }
      return this.$store.getters['radios/types'][this.type]
    },
    customRadioId: function () {
      if (this.customRadio) {
        return this.customRadio.id
      }
      return null
    }
  }
}
</script>
