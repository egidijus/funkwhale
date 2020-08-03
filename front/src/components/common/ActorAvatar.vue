<template>
  <img alt="" v-if="actor.icon && actor.icon.urls.original" :src="actor.icon.urls.medium_square_crop" class="ui avatar circular image" />
  <span v-else :style="defaultAvatarStyle" class="ui avatar circular label">{{ actor.preferred_username[0]}}</span>
</template>

<script>
import {hashCode, intToRGB} from '@/utils/color'

export default {
  props: ['actor'],
  computed: {
    actorColor () {
      return intToRGB(hashCode(this.actor.full_username))
    },
    defaultAvatarStyle () {
      return {
        'background-color': `#${this.actorColor}`
      }
    }
  }
}
</script>
