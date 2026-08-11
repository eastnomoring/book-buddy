<script setup lang="ts">
import type { ToolEvent } from '../platform/chatTransport'

defineProps<{
  events: ToolEvent[]
  /** tool_result.images 落盘后的本地路径，按 tool id 索引 */
  imagePaths?: Record<string, string[]>
}>()
</script>

<template>
  <view class="tool-events">
    <view
      v-for="ev in events"
      :key="ev.id"
      class="tool-event"
      :class="{
        running: ev.type === 'tool_call',
        failed: ev.type === 'tool_result' && !ev.ok,
      }"
    >
      <view class="tool-head">
        <text class="tool-name">{{ ev.name }}</text>
        <text class="tool-status">
          {{ ev.type === 'tool_call' ? '运行中…' : ev.ok ? '完成' : '失败' }}
        </text>
      </view>
      <text
        v-if="ev.type === 'tool_result' && ev.preview"
        class="tool-preview"
      >{{ ev.preview }}</text>
      <view
        v-if="imagePaths?.[ev.id]?.length"
        class="tool-images"
      >
        <image
          v-for="(src, imgIdx) in imagePaths[ev.id]"
          :key="`${ev.id}-${imgIdx}`"
          class="tool-image"
          :src="src"
          mode="widthFix"
        />
      </view>
    </view>
  </view>
</template>

<style scoped>
.tool-events {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-bottom: 0.25rem;
}

.tool-event {
  padding: 0.4rem 0.55rem;
  border: 1px solid rgba(26, 107, 92, 0.2);
  border-radius: 10px;
  background: rgba(26, 107, 92, 0.06);
}

.tool-event.failed {
  border-color: rgba(180, 35, 24, 0.3);
  background: rgba(180, 35, 24, 0.06);
}

.tool-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
}

.tool-name {
  font-size: 0.72rem;
  font-weight: 500;
  color: #1a6b5c;
}

.tool-event.failed .tool-name {
  color: #b42318;
}

.tool-status {
  font-size: 0.65rem;
  color: #6b7884;
}

.tool-preview {
  display: block;
  margin-top: 0.3rem;
  padding: 0.35rem 0.4rem;
  border-radius: 6px;
  background: rgba(21, 32, 40, 0.05);
  font-size: 0.65rem;
  line-height: 1.45;
  color: #3d4a55;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 8rem;
  overflow-y: auto;
}

.tool-images {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: 0.35rem;
}

.tool-image {
  width: 100%;
  border-radius: 8px;
  border: 1px solid rgba(21, 32, 40, 0.1);
  background: #fff;
}
</style>
