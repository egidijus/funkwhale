<template>
  <span class="component-user-link">
    <template v-if="avatar">
      <img
        class="ui tiny circular avatar"
        alt=""
        v-if="user.avatar && user.avatar.urls.medium_square_crop"
        v-lazy="$store.getters['instance/absoluteUrl'](user.avatar.urls.medium_square_crop)" />
      <span v-else :style="defaultAvatarStyle" class="ui circular label">{{ user.username[0]}}</span>
      &nbsp;
    </template>
    @{{ user.username }}
  </span>
</template>

<script>
import {hashCode, intToRGB} from '@/utils/color'

export default {
  props: {
    user: {required: true},
    avatar: {type: Boolean, default: true}
  },
  computed: {
    userColor () {
      return intToRGB(hashCode(this.user.username + String(this.user.id)))
    },
    defaultAvatarStyle () {
      return {
        'background-color': `#${this.userColor}`
      }
    }
  }
}
</script>
