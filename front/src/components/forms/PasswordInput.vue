<template>
  <div class="ui fluid action input">
    <input
    required
    name="password"
    :type="passwordInputType"
    @input="$emit('input', $event.target.value)"
    :id="fieldId"
    :value="value">
    <button @click.prevent="showPassword = !showPassword" type="button" :title="labels.title" class="ui icon button">
      <i class="eye icon"></i>
    </button>
    <button v-if="copyButton" @click.prevent="copy" type="button" class="ui icon button" :title="labels.copy">
      <i class="copy icon"></i>
    </button>
  </div>
</template>
<script>

function copyStringToClipboard (str) {
  // cf https://techoverflow.net/2018/03/30/copying-strings-to-the-clipboard-using-pure-javascript/
  let el = document.createElement('textarea');
  el.value = str;
  el.setAttribute('readonly', '');
  el.style = {position: 'absolute', left: '-9999px'};
  document.body.appendChild(el);
  el.select();
  document.execCommand('copy');
  document.body.removeChild(el);
}

export default {
  props: ['value', 'defaultShow', 'copyButton', 'fieldId'],
  data () {
    return {
      showPassword: this.defaultShow || false,
    }
  },
  computed: {
    labels () {
      return {
        title: this.$pgettext('Content/Settings/Button.Tooltip/Verb', 'Show/hide password'),
        copy: this.$pgettext('*/*/Button.Label/Short, Verb', 'Copy')
      }
    },
    passwordInputType () {
      if (this.showPassword) {
        return 'text'
      }
      return 'password'
    }
  },
  methods: {
    copy () {
      copyStringToClipboard(this.value)
    }
  }
}
</script>
