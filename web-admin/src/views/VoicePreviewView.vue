<script setup lang="ts">
import { onBeforeUnmount, ref } from "vue";

import { previewVoice } from "../lib/api";

const voices = [
  {
    value: "zh-CN-XiaoxiaoNeural",
    label: "晓晓 / 中文女声",
  },
  {
    value: "zh-CN-XiaoyiNeural",
    label: "晓伊 / 中文女声",
  },
  {
    value: "zh-CN-YunxiNeural",
    label: "云希 / 中文男声",
  },
  {
    value: "zh-CN-YunjianNeural",
    label: "云健 / 中文男声",
  },
];

const text = ref(
  "你好，我是 Nagi……很高兴在网页里和你说话。",
);
const voice = ref(voices[0].value);
const audioUrl = ref("");
const loading = ref(false);
const error = ref("");
const successMessage = ref("");

function clearAudio() {
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value);
    audioUrl.value = "";
  }
}

async function generatePreview() {
  if (!text.value.trim() || loading.value) return;

  loading.value = true;
  error.value = "";
  successMessage.value = "";
  clearAudio();

  try {
    const audioBlob = await previewVoice({
      text: text.value.trim(),
      voice: voice.value,
    });

    audioUrl.value = URL.createObjectURL(audioBlob);
    successMessage.value = "试听已生成，可以播放音频";
  } catch (e) {
    error.value = e instanceof Error
      ? e.message
      : "试听生成失败";
  } finally {
    loading.value = false;
  }
}

onBeforeUnmount(clearAudio);
</script>

<template>
  <section class="view">
    <div class="view-heading">
      <div>
        <h1>音色试听</h1>
        <p class="view-intro">
          使用 Edge TTS 生成临时语音，比较不同中文音色。
        </p>
      </div>
    </div>

    <form
      class="voice-form"
      @submit.prevent="generatePreview"
    >
      <div class="form-field">
        <label for="voice-select">
          <span>音色</span>
        </label>

        <select
          id="voice-select"
          v-model="voice"
          class="filter-control"
          :disabled="loading"
        >
          <option
            v-for="item in voices"
            :key="item.value"
            :value="item.value"
          >
            {{ item.label }}
          </option>
        </select>
      </div>

      <div class="form-field">
        <label for="preview-text">
          <span>试听文本</span>
          <span class="field-meta">
            {{ text.length }} / 200
          </span>
        </label>

        <textarea
          id="preview-text"
          v-model="text"
          class="voice-textarea"
          maxlength="200"
          :disabled="loading"
        ></textarea>
      </div>

      <div class="form-actions">
        <button
          class="primary-button"
          type="submit"
          :disabled="!text.trim() || loading"
        >
          {{ loading ? "生成中…" : "生成试听" }}
        </button>
      </div>
    </form>

    <p
      v-if="error"
      class="page-state save-error"
      role="alert"
    >
      {{ error }}
    </p>

    <p
      v-if="successMessage"
      class="save-success voice-success"
      role="status"
    >
      {{ successMessage }}
    </p>

    <div v-if="audioUrl" class="audio-player">
      <audio
        :src="audioUrl"
        controls
        preload="auto"
      >
        当前浏览器不支持音频播放。
      </audio>

      <p>
        临时音频仅用于试听，不会保存到对话记录。
      </p>
    </div>
  </section>
</template>