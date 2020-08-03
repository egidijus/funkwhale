<template>
  <div class="ui segment component-fs-logs">
    <div class="ui active dimmer" v-if="data.status === 'pending'">
      <div class="ui text loader">
        <translate translate-context="Content/Library/Paragraph">Import hasn't started yet</translate>
      </div>
    </div>
    <template v-else v-for="(row, idx) in data.logs">
      <p :key="idx">{{ row }}</p>
    </template>
  </div>
</template>
<script>
export default {
  props: ["data"],
}
</script>