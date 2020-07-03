<template>
  <modal class="small" :show.sync="show">
    <h4 class="header">
      <translate key="1" v-if="channel.content_category === 'podcasts'" translate-context="Popup/Channels/Title/Verb">New serie</translate>
      <translate key="2" v-else translate-context="Popup/Channels/Title">New album</translate>
    </h4>
    <div class="scrolling content">
      <channel-album-form
        ref="albumForm"
        @loading="isLoading = $event"
        @submittable="submittable = $event"
        @created="$emit('created', $event)"
        :channel="channel"></channel-album-form>
    </div>
    <div class="actions">
      <button class="ui basic cancel button"><translate translate-context="*/*/Button.Label/Verb">Cancel</translate></button>
      <button :class="['ui', 'primary', {loading: isLoading}, 'button']" :disabled="!submittable" @click.stop.prevent="$refs.albumForm.submit()">
        <translate translate-context="*/*/Button.Label">Create</translate>
      </button>
    </div>
  </modal>
</template>

<script>
import Modal from '@/components/semantic/Modal'
import ChannelAlbumForm from '@/components/channels/AlbumForm'

export default {
  props: ['channel'],
  components: {
    Modal,
    ChannelAlbumForm
  },
  data () {
    return {
      isLoading: false,
      submittable: false,
      show: false,
    }
  },
  watch: {
    show () {
      this.isLoading = false
      this.submittable = false
    }
  }
}
</script>
