<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, RouterView } from "vue-router";

import {
  getHealth,
  type HealthResponse,
} from "./lib/api";

const health = ref<HealthResponse | null>(null);
const loading = ref(false);
const error = ref("");

const healthLabel = computed(() => {
  if (loading.value) return "正在检查服务";
  if (error.value) return "后端连接失败";
  if (!health.value) return "尚未检查";
  return "后端服务正常";
});

const healthClass = computed(() => {
  if (loading.value) return "is-checking";
  if (error.value) return "is-error";
  if (!health.value) return "is-idle";
  return "is-ok";
});

async function loadHealth() {
  loading.value = true;
  error.value = "";

  try {
    health.value = await getHealth();
  } catch (e) {
    health.value = null;
    error.value = e instanceof Error
      ? e.message
      : "无法连接后端";
  } finally {
    loading.value = false;
  }
}

onMounted(loadHealth);
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div>
        <RouterLink class="brand" to="/persona">
          <span class="brand-name">Nagi</span>
          <span class="brand-subtitle">角色管理台</span>
        </RouterLink>

        <nav class="main-nav" aria-label="管理后台导航">
        <RouterLink to="/persona">
            人设配置
        </RouterLink>
        <RouterLink to="/conversations">
            对话日志
        </RouterLink>
        <RouterLink to="/voice">
            音色试听
        </RouterLink>
        </nav>
      </div>

      <section class="service-panel" aria-live="polite">
        <div class="service-heading">
          <span class="status-dot" :class="healthClass"></span>
          <strong>{{ healthLabel }}</strong>
        </div>

        <p v-if="health" class="service-meta">
          MySQL / {{ health.mysql }}<br>
          Redis / {{ health.redis }}
        </p>

        <p v-if="error" class="service-error">
          {{ error }}
        </p>

        <button
          class="outline-button"
          type="button"
          :disabled="loading"
          @click="loadHealth"
        >
          {{ loading ? "检查中…" : "重新检查" }}
        </button>
      </section>
    </aside>

    <main class="main-content">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
  </div>
</template>