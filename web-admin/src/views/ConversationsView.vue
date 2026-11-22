<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  getConversations,
  getEmotionStats,
  type ConversationRecord,
  type EmotionStat,
} from "../lib/api";

const records = ref<ConversationRecord[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

const sessionFilter = ref("");
const emotionFilter = ref("");

const loading = ref(false);
const error = ref("");

const totalPages = computed(() => {
  return Math.max(
    1,
    Math.ceil(total.value / pageSize.value),
  );
});

const hasPrevious = computed(() => {
  return page.value > 1 && !loading.value;
});

const hasNext = computed(() => {
  return page.value < totalPages.value && !loading.value;
});

const emotionLabels: Record<string, string> = {
  neutral: "平静",
  happy: "开心",
  confused: "疑惑",
  sad: "难过",
};

const emotionStats = ref<EmotionStat[]>([]);
const statsError = ref("");

const statsTotal = computed(() => {
  return emotionStats.value.reduce(
    (sum, item) => sum + item.count,
    0,
  );
});

const maxEmotionCount = computed(() => {
  return Math.max(
    1,
    ...emotionStats.value.map((item) => item.count),
  );
});

function emotionLabel(value: string): string {
  return emotionLabels[value] ?? value;
}

function emotionPercentage(count: number): number {
  if (statsTotal.value === 0) return 0;
  return Math.round((count / statsTotal.value) * 100);
}

async function loadEmotionStats() {
  statsError.value = "";

  try {
    emotionStats.value = await getEmotionStats();
  } catch (e) {
    statsError.value = e instanceof Error
      ? e.message
      : "情绪统计读取失败";
  }
}

async function refreshData() {
  await Promise.all([
    loadConversations(),
    loadEmotionStats(),
  ]);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function shortId(value: string): string {
  if (value.length <= 12) return value;
  return `${value.slice(0, 8)}…`;
}

async function loadConversations() {
  loading.value = true;
  error.value = "";

  try {
    const data = await getConversations({
      page: page.value,
      page_size: pageSize.value,
      session_id: sessionFilter.value,
      emotion: emotionFilter.value,
    });

    records.value = data.items;
    total.value = data.total;

    // 如果删除或筛选导致当前页超出范围，回到最后一页
    if (
      data.items.length === 0
      && data.total > 0
      && page.value > 1
    ) {
      page.value = Math.ceil(
        data.total / pageSize.value,
      );
      await loadConversations();
    }
  } catch (e) {
    error.value = e instanceof Error
      ? e.message
      : "对话记录读取失败";
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  page.value = 1;
  refreshData();
}

function resetFilters() {
  sessionFilter.value = "";
  emotionFilter.value = "";
  page.value = 1;
  pageSize.value = 10;
  refreshData();
}

function filterBySession(sessionId: string) {
  sessionFilter.value = sessionId;
  emotionFilter.value = "";
  page.value = 1;
  refreshData();
}

function goToPage(target: number) {
  if (
    target < 1
    || target > totalPages.value
    || target === page.value
  ) {
    return;
  }

  page.value = target;
  loadConversations();
}

onMounted(refreshData);
</script>

<template>
  <section class="view conversations-view">
    <div class="view-heading">
      <div>
        <h1>对话日志</h1>
        <p class="view-intro">
          查看已写入 MySQL 的用户输入、角色回复与会话信息。
        </p>
      </div>
    </div>

    <section
      class="emotion-stats"
      aria-labelledby="emotion-stats-title"
    >
      <div class="stats-heading">
        <div>
          <h2 id="emotion-stats-title">情绪分布</h2>
          <p>全部对话 / 共 {{ statsTotal }} 条</p>
        </div>
      </div>

      <p
        v-if="statsError"
        class="save-error"
        role="alert"
      >
        {{ statsError }}
      </p>

      <p
        v-else-if="emotionStats.length === 0"
        class="stats-empty"
      >
        暂无可统计的对话记录
      </p>

      <div v-else class="stats-list">
        <div
          v-for="stat in emotionStats"
          :key="stat.emotion"
          class="stat-row"
        >
          <div class="stat-label">
            <span>{{ emotionLabel(stat.emotion) }}</span>
            <span>
              {{ stat.count }} 条 / {{ emotionPercentage(stat.count) }}%
            </span>
          </div>

          <div
            class="stat-track"
            role="img"
            :aria-label="`${emotionLabel(stat.emotion)}：${stat.count} 条，占 ${emotionPercentage(stat.count)}%`"
          >
            <div
              class="stat-bar"
              :style="{
                transform: `scaleX(${stat.count / maxEmotionCount})`,
              }"
            ></div>
          </div>
        </div>
      </div>
    </section>

    <form
      class="log-filters"
      @submit.prevent="applyFilters"
    >
      <label>
        <span>会话 ID</span>
        <input
          v-model="sessionFilter"
          class="filter-control"
          type="text"
          maxlength="64"
          placeholder="输入完整 session_id"
          :disabled="loading"
        >
      </label>

      <label>
        <span>情绪</span>
        <select
          v-model="emotionFilter"
          class="filter-control"
          :disabled="loading"
        >
          <option value="">全部情绪</option>
          <option value="neutral">平静</option>
          <option value="happy">开心</option>
          <option value="confused">疑惑</option>
          <option value="sad">难过</option>
        </select>
      </label>

      <label>
        <span>每页条数</span>
        <select
          v-model.number="pageSize"
          class="filter-control"
          :disabled="loading"
        >
          <option :value="10">10 条</option>
          <option :value="20">20 条</option>
          <option :value="50">50 条</option>
        </select>
      </label>

      <div class="filter-actions">
        <button
          class="primary-button"
          type="submit"
          :disabled="loading"
        >
          查询
        </button>
        <button
          class="outline-button"
          type="button"
          :disabled="loading"
          @click="resetFilters"
        >
          重置
        </button>
      </div>
    </form>

    <div class="log-summary" aria-live="polite">
      <span>共 {{ total }} 条记录</span>
      <span v-if="loading">正在更新……</span>
      <span v-else>
        第 {{ page }} / {{ totalPages }} 页
      </span>
    </div>

    <div
      v-if="error"
      class="page-state"
      role="alert"
    >
      <p class="save-error">{{ error }}</p>
      <button
        class="outline-button"
        type="button"
        @click="loadConversations"
      >
        重试
      </button>
    </div>

    <div
      v-else-if="!loading && records.length === 0"
      class="page-state empty-state"
    >
      <strong>没有匹配的对话记录</strong>
      <p>
        可以重置筛选条件，或先通过 Unity／WebSocket 测试客户端完成一次真实对话。
      </p>
    </div>

    <div v-if="records.length > 0" class="table-scroll">
      <table class="conversation-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>用户输入</th>
            <th>Nagi 回复</th>
            <th>情绪</th>
            <th>会话</th>
            <th>详情</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="record in records" :key="record.id">
            <td class="time-cell">
              {{ formatDate(record.created_at) }}
            </td>

            <td>
              <p class="truncated-text">
                {{ record.user_text }}
              </p>
            </td>

            <td>
              <p class="truncated-text">
                {{ record.assistant_text }}
              </p>
            </td>

            <td class="emotion-cell">
              {{ emotionLabel(record.emotion) }}
            </td>

            <td>
              <button
                class="session-link"
                type="button"
                :title="`筛选会话：${record.session_id}`"
                @click="filterBySession(record.session_id)"
              >
                {{ shortId(record.session_id) }}
              </button>
            </td>

            <td>
              <details class="record-details">
                <summary>查看</summary>

                <div class="record-full">
                  <dl>
                    <dt>Session ID</dt>
                    <dd>{{ record.session_id }}</dd>
                    <dt>Request ID</dt>
                    <dd>{{ record.request_id }}</dd>
                    <dt>用户输入</dt>
                    <dd>{{ record.user_text }}</dd>
                    <dt>Nagi 回复</dt>
                    <dd>{{ record.assistant_text }}</dd>
                  </dl>
                </div>
              </details>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <nav
      v-if="total > 0"
      class="pagination"
      aria-label="对话日志分页"
    >
      <button
        class="outline-button"
        type="button"
        :disabled="!hasPrevious"
        @click="goToPage(page - 1)"
      >
        上一页
      </button>

      <button
        class="outline-button"
        type="button"
        :disabled="!hasNext"
        @click="goToPage(page + 1)"
      >
        下一页
      </button>
    </nav>
  </section>
</template>