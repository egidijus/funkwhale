<template>
  <div class="ui small placeholder segment component-placeholder component-empty-state">
    <h4 class="ui header">
      <div class="content">
        <slot name="title">

          <i class="search icon"></i>
          <translate translate-context="Content/*/Paragraph">
            No results were found.
          </translate>
        </slot>
      </div>
    </h4>
    <div class="inline center aligned text">
      <slot></slot>
      <button v-if="refresh" class="ui button" @click="$emit('refresh')">
        <translate translate-context="Content/*/Button.Label/Short, Verb">
          Refresh
        </translate>
      </button>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    refresh: {type: Boolean, default: false}
  }
}
</script>
