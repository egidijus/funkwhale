<template>
  <div :class="['ui', {loading}, 'segment']">
    <div class="ui fluid action input">
      <input class="ui disabled" disabled :value="data.root + '/' + value.join('/')" />
      <button class="ui button" @click.prevent="$emit('import')">
        <translate translate-context="Content/Library/Button/Verb">Import</translate>
      </button>
    </div>
    <div class="ui list component-fs-browser">
      <a
        v-if="value.length > 0"
        class="item"
        href=""
        @click.prevent="handleClick({name: '..', dir: true})"
        >
        <i class="folder icon"></i>
        <div class="content">
          <div class="header">..</div>
        </div>
      </a>
      <a
        class="item"
        href=""
        @click.prevent="handleClick(e)"
        v-for="e in data.content"
        :key="e.name">
        <i class="folder icon" v-if="e.dir"></i>
        <i class="file icon" v-else></i>
        <div class="content">
          <div class="header">{{ e.name }}</div>
        </div>
      </a>
    </div>
  </div>
</template>
<script>
export default {
  props: ["data", "loading", "value"],
  methods: {
    handleClick (element) {
      if (!element.dir) {
        return
      }
      if (element.name === "..") {
        let newValue = [...this.value]
        newValue.pop()
        this.$emit('input', newValue)
      } else {
        this.$emit('input', [...this.value, element.name])
      }
    }
  }
}
</script>