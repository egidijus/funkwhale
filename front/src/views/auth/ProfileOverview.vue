<template>
  <section>
    <div v-if="$store.getters['ui/layoutVersion'] === 'small'">
      <rendered-description
        @updated="$emit('updated', $event)"
        :content="object.summary"
        :field-name="'summary'"
        :update-url="`users/${$store.state.auth.username}/`"
        :can-update="$store.state.auth.authenticated && object.full_username === $store.state.auth.fullUsername"></rendered-description>
      <div class="ui hidden divider"></div>
    </div>
    <div>
      <h2 class="ui with-actions header">
        <translate translate-context="*/*/*">Channels</translate>
        <div class="actions" v-if="$store.state.auth.authenticated && object.full_username === $store.state.auth.fullUsername">
          <a @click.stop.prevent="showCreateModal = true">
            <i class="plus icon"></i>
            <translate translate-context="Content/Profile/Button">Add new</translate>
          </a>
        </div>
      </h2>
      <channels-widget :filters="{scope: `actor:${object.full_username}`}"></channels-widget>
      <h2 class="ui with-actions header">
        <translate translate-context="Content/Profile/Header">User Libraries</translate>
        <div class="actions" v-if="$store.state.auth.authenticated && object.full_username === $store.state.auth.fullUsername">
          <router-link :to="{name: 'content.libraries.index'}">
            <i class="plus icon"></i>
            <translate translate-context="Content/Profile/Button">Add new</translate>
          </router-link>
        </div>
      </h2>
      <library-widget :url="`federation/actors/${object.full_username}/libraries/`">
        <translate translate-context="Content/Profile/Paragraph" slot="title">This user shared the following libraries...</translate>
      </library-widget>
    </div>

    <modal :show.sync="showCreateModal">
      <h4 class="header">
        <translate v-if="step === 1" key="1" translate-context="Content/Channel/*/Verb">Create channel</translate>
        <translate v-else-if="category === 'podcast'" key="2" translate-context="Content/Channel/*">Podcast channel</translate>
        <translate v-else key="3" translate-context="Content/Channel/*">Artist channel</translate>
      </h4>
      <div class="scrolling content" ref="modalContent">
        <channel-form
          ref="createForm"
          :object="null"
          :step="step"
          @loading="isLoading = $event"
          @submittable="submittable = $event"
          @category="category = $event"
          @errored="$refs.modalContent.scrollTop = 0"
          @created="$router.push({name: 'channels.detail', params: {id: $event.actor.preferred_username}})"></channel-form>
          <div class="ui hidden divider"></div>
      </div>
      <div class="actions">
        <div v-if="step === 1" class="ui basic deny button">
          <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
        </div>
        <button v-if="step > 1" class="ui basic button" @click.stop.prevent="step -= 1">
          <translate translate-context="*/*/Button.Label/Verb">Previous step</translate>
        </button>
        <button v-if="step === 1" class="ui primary button" @click.stop.prevent="step += 1">
          <translate translate-context="*/*/Button.Label">Next step</translate>
        </button>
        <button v-if="step === 2" :class="['ui', 'primary button', {loading: isLoading}]" type="submit" @click.prevent.stop="$refs.createForm.submit" :disabled="!submittable && !isLoading">
          <translate translate-context="*/Channels/Button.Label">Create channel</translate>
        </button>
      </div>
    </modal>

  </section>
</template>

<script>
import Modal from '@/components/semantic/Modal'
import LibraryWidget from "@/components/federation/LibraryWidget"
import ChannelsWidget from "@/components/audio/ChannelsWidget"
import ChannelForm from "@/components/audio/ChannelForm"

export default {
  props: ['object'],
  components: {ChannelsWidget, LibraryWidget, ChannelForm, Modal},
  data () {
    return {
      showCreateModal: false,
      isLoading: false,
      submittable: false,
      step: 1,
      category: 'podcast',
    }
  }
}
</script>
