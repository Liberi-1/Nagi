<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { onBeforeRouteLeave } from "vue-router";

import {
  getActivePersona,
  updateActivePersona,
  type Persona,
} from "../lib/api";

const persona = ref<Persona | null>(null);
const name = ref("");
const content = ref("");

const loading = ref(false);
const saving = ref(false);
const loadError = ref("");
const saveError = ref("");
const successMessage = ref("");

const isDirty = computed(() => {
  if (!persona.value) return false;

  return (
    name.value !== persona.value.name
    || content.value !== persona.value.content
  );
});

const nameError = computed(() => {
  if (!name.value.trim()) return "人设名称不能为空";
  if (name.value.length > 100) return "名称不能超过 100 个字符";
  return "";
});

const contentError = computed(() => {
  if (!content.value.trim()) return "人设内容不能为空";
  if (content.value.length > 20000) {
    return "人设内容不能超过 20000 个字符";
  }
  return "";
});

const canSave = computed(() => {
  return (
    persona.value !== null
    && isDirty.value
    && !nameError.value
    && !contentError.value
    && !saving.value
  );
});

const updatedAtText = computed(() => {
  if (!persona.value) return "";

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(persona.value.updated_at));
});

function confirmDiscardChanges(): boolean {
  if (!isDirty.value) return true;

  return window.confirm(
    "当前人设尚未保存，确定放弃这些修改吗？",
  );
}

async function loadPersona(requireConfirmation = false) {
  if (
    requireConfirmation
    && !confirmDiscardChanges()
  ) {
    return;
  }

  loading.value = true;
  loadError.value = "";
  saveError.value = "";
  successMessage.value = "";

  try {
    const data = await getActivePersona();

    persona.value = data;
    name.value = data.name;
    content.value = data.content;
  } catch (e) {
    loadError.value = e instanceof Error
      ? e.message
      : "人设读取失败";
  } finally {
    loading.value = false;
  }
}

async function savePersona() {
  if (!canSave.value) return;

  saving.value = true;
  saveError.value = "";
  successMessage.value = "";

  try {
    const updated = await updateActivePersona({
      name: name.value.trim(),
      content: content.value.trim(),
    });

    persona.value = updated;
    name.value = updated.name;
    content.value = updated.content;
    successMessage.value = "人设已保存，下一轮对话即可使用";
  } catch (e) {
    // 不把失败响应写回表单，因此用户输入会原样保留
    saveError.value = e instanceof Error
      ? e.message
      : "保存失败，请稍后重试";
  } finally {
    saving.value = false;
  }
}

function handleBeforeUnload(event: BeforeUnloadEvent) {
  if (!isDirty.value) return;

  event.preventDefault();
  event.returnValue = "";
}

watch([name, content], () => {
  saveError.value = "";
  successMessage.value = "";
});

onBeforeRouteLeave(() => {
  return confirmDiscardChanges();
});

onMounted(() => {
  window.addEventListener(
    "beforeunload",
    handleBeforeUnload,
  );
  loadPersona();
});

onBeforeUnmount(() => {
  window.removeEventListener(
    "beforeunload",
    handleBeforeUnload,
  );
});
</script>

<template>
  <section class="view">
    <div class="view-heading">
      <div>
        <h1>人设配置</h1>
        <p class="view-intro">
          修改 Nagi 的身份、性格、说话方式与口播规则。
        </p>
      </div>

      <button
        class="outline-button reload-button"
        type="button"
        :disabled="loading || saving"
        @click="loadPersona(true)"
      >
        {{ loading ? "读取中…" : "重新读取" }}
      </button>
    </div>

    <p
      v-if="loading && !persona"
      class="page-state"
      role="status"
    >
      正在从数据库读取当前人设……
    </p>

    <div
      v-else-if="loadError && !persona"
      class="page-state"
      role="alert"
    >
      <p class="save-error">{{ loadError }}</p>
      <button
        class="outline-button"
        type="button"
        @click="loadPersona()"
      >
        重试
      </button>
    </div>

    <template v-else-if="persona">
      <div class="persona-meta">
        <span>人设 ID / {{ persona.id }}</span>
        <span>最后更新 / {{ updatedAtText }}</span>
        <span v-if="isDirty" class="dirty-state">
          有未保存修改
        </span>
      </div>

      <form
        class="persona-form"
        @submit.prevent="savePersona"
      >
        <div class="form-field">
          <label for="persona-name">
            <span>人设名称</span>
            <span class="field-meta">
              {{ name.length }} / 100
            </span>
          </label>

          <input
            id="persona-name"
            v-model="name"
            type="text"
            maxlength="100"
            autocomplete="off"
            :disabled="saving"
          >

          <p v-if="nameError" class="field-error">
            {{ nameError }}
          </p>
        </div>

        <div class="form-field">
          <label for="persona-content">
            <span>System Prompt / Markdown</span>
            <span class="field-meta">
              {{ content.length }} / 20000
            </span>
          </label>

          <textarea
            id="persona-content"
            v-model="content"
            maxlength="20000"
            :disabled="saving"
            spellcheck="false"
          ></textarea>

          <p class="field-help">
            这里保存的是完整 system prompt。
            支持 Markdown，但不要求模型以 Markdown 格式回复。
          </p>

          <p v-if="contentError" class="field-error">
            {{ contentError }}
          </p>
        </div>

        <div class="form-actions">
          <button
            class="primary-button"
            type="submit"
            :disabled="!canSave"
          >
            {{ saving ? "保存中…" : "保存人设" }}
          </button>

          <p
            v-if="successMessage"
            class="save-success"
            role="status"
          >
            {{ successMessage }}
          </p>

          <p
            v-if="saveError"
            class="save-error"
            role="alert"
          >
            {{ saveError }}；当前输入已保留。
          </p>
        </div>
      </form>
    </template>
  </section>
</template>