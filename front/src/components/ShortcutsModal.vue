<template>
  <modal @update:show="$emit('update:show', $event)" :show="show">
    <header class="header">
      <translate translate-context="*/*/*/Noun">Keyboard shortcuts</translate>
    </header>
    <section class="scrolling content">
      <div class="ui stackable two column grid">
        <div class="column">
          <table
            class="ui compact basic table"
            v-for="section in player"
            :key="section.title">
          <caption>{{ section.title }}</caption>
          <tbody>
            <tr v-for="shortcut in section.shortcuts" :key="shortcut.summary">
              <td>{{ shortcut.summary }}</td>
              <td><span class="ui label">{{ shortcut.key }}</span></td>
            </tr>
          </tbody>
          </table>
        </div>
        <div class="column">
          <table
            class="ui compact basic table"
            v-for="section in general"
            :key="section.title">
          <caption>{{ section.title }}</caption>
          <tbody>
            <tr v-for="shortcut in section.shortcuts" :key="shortcut.summary">
              <td>{{ shortcut.summary }}</td>
              <td><span class="ui label">{{ shortcut.key }}</span></td>
            </tr>
          </tbody>
          </table>
        </div>
      </div>
    </section>
    <footer class="actions">
      <div class="ui basic cancel button"><translate translate-context="*/*/Button.Label/Verb">Close</translate></div>
    </footer>
  </modal>
</template>

<script>

export default {
  props: ['show'],
  components: {
    Modal:  () => import(/* webpackChunkName: "modal" */ "@/components/semantic/Modal"),
  },
  computed: {
    general () {
      return [
        {
          title: this.$pgettext('Popup/Keyboard shortcuts/Title', 'General shortcuts'),
          shortcuts: [
            {
              key: 'h',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Show available keyboard shortcuts')
            },
            {
              key: 'shift + f',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Focus searchbar')
            },
            {
              key: 'esc',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Unfocus searchbar')
            },
          ]
        },
      ]
    },
        // space.prevent.exact="togglePlay"
        // ctrl.shift.left.prevent.exact="previous"
        // ctrl.shift.right.prevent.exact="next"
        // shift.down.prevent.exact="$store.commit('player/incrementVolume', -0.1)"
        // shift.up.prevent.exact="$store.commit('player/incrementVolume', 0.1)"
        // right.prevent.exact="seek (5)"
        // left.prevent.exact="seek (-5)"
        // shift.right.prevent.exact="seek (30)"
        // shift.left.prevent.exact="seek (-30)"
        // m.prevent.exact="toggleMute"
        // l.prevent.exact="$store.commit('player/toggleLooping')"
        // s.prevent.exact="shuffle"
        // f.prevent.exact="$store.dispatch('favorites/toggle', currentTrack.id)"
        // q.prevent.exact="clean"

    player () {
      return [
        {
          title: this.$pgettext('Popup/Keyboard shortcuts/Title', 'Audio player shortcuts'),
          shortcuts: [
            {
              key: 'space',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Pause/play the current track')
            },
            {
              key: 'left',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Seek backwards 5s')
            },
            {
              key: 'right',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Seek forwards 5s')
            },
            {
              key: 'shift + left',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Seek backwards 30s')
            },
            {
              key: 'shift + right',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Seek forwards 30s')
            },
            {
              key: 'ctrl + shift + left',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Play previous track')
            },
            {
              key: 'ctrl + shift + right',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Play next track')
            },
            {
              key: 'shift + up',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Increase volume')
            },
            {
              key: 'shift + down',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Decrease volume')
            },
            {
              key: 'm',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Toggle mute')
            },
            {
              key: 'e',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Expand queue/player view')
            },
            {
              key: 'l',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Toggle queue looping')
            },
            {
              key: 's',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Shuffle queue')
            },
            {
              key: 'q',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Clear queue')
            },
            {
              key: 'f',
              summary: this.$pgettext('Popup/Keyboard shortcuts/Table.Label/Verb', 'Toggle favorite')
            },
          ]
        }
      ]
    }
  }
}
</script>
