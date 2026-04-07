<template>
  <div class="sandbox-panel">
    <!-- 顶部提示 -->
    <n-collapse :default-expanded-names="['help']">
      <n-collapse-item title="💡 使用说明" name="help">
        <n-text depth="3" style="font-size: 12px; line-height: 1.6">
          <strong>角色锚点</strong>：设置角色的心理状态、口头禅、小动作，章节生成时会自动注入。
          <br />
          <strong>对话白名单</strong>：从已生成章节中提取的重要对话，可用于参考角色声线。
        </n-text>
      </n-collapse-item>
    </n-collapse>

    <!-- 角色锚点卡片 -->
    <n-card title="🎭 角色锚点" size="small" :bordered="true">
      <template #header-extra>
        <n-text v-if="characters.length > 0" depth="3" style="font-size: 12px">
          共 {{ characters.length }} 个角色
        </n-text>
      </template>

      <n-space vertical :size="12">
        <!-- 无角色提示 -->
        <n-alert
          v-if="characters.length === 0 && !charLoading"
          type="warning"
          :show-icon="true"
          style="font-size: 12px"
        >
          当前 Bible 中没有角色，请先在「剧本基建」中添加角色。
        </n-alert>

        <!-- 角色选择 -->
        <n-select
          v-model:value="selectedCharacterId"
          :options="characterOptions"
          placeholder="选择角色编辑锚点"
          filterable
          clearable
          :loading="charLoading"
          @update:value="onCharacterSelect"
        />

        <!-- 锚点编辑区 -->
        <n-spin :show="anchorLoading">
          <template v-if="anchor">
            <n-space vertical :size="10">
              <n-grid :cols="3" :x-gap="10">
                <n-gi>
                  <div class="anchor-field">
                    <n-text class="anchor-label">心理状态</n-text>
                    <n-input v-model:value="editMental" size="small" placeholder="如：平静、焦虑" />
                  </div>
                </n-gi>
                <n-gi>
                  <div class="anchor-field">
                    <n-text class="anchor-label">口头禅</n-text>
                    <n-input v-model:value="editVerbal" size="small" placeholder="如：嗯...、岂有此理" />
                  </div>
                </n-gi>
                <n-gi>
                  <div class="anchor-field">
                    <n-text class="anchor-label">小动作</n-text>
                    <n-input v-model:value="editIdle" size="small" placeholder="如：摸剑柄、转笔" />
                  </div>
                </n-gi>
              </n-grid>

              <!-- 场景测试 -->
              <n-collapse>
                <n-collapse-item title="🧪 试生成对话" name="test">
                  <n-space vertical :size="8">
                    <n-input
                      v-model:value="scenePrompt"
                      type="textarea"
                      size="small"
                      placeholder="描述一个场景，测试角色声线..."
                      :autosize="{ minRows: 2, maxRows: 4 }"
                    />
                    <n-space :size="8">
                      <n-button
                        type="primary"
                        size="small"
                        :loading="genLoading"
                        :disabled="!scenePrompt.trim()"
                        @click="runGenerate"
                      >
                        生成对话
                      </n-button>
                      <n-button
                        size="small"
                        :loading="saveLoading"
                        @click="saveAnchors"
                      >
                        保存锚点
                      </n-button>
                    </n-space>
                    <n-card v-if="generatedLine" size="small" :bordered="true" class="generated-output">
                      <n-text style="font-size: 13px; line-height: 1.7">{{ generatedLine }}</n-text>
                    </n-card>
                  </n-space>
                </n-collapse-item>
              </n-collapse>
            </n-space>
          </template>
          <n-empty v-else-if="selectedCharacterId && !anchorLoading" description="选择角色查看锚点" size="small" />
        </n-spin>
      </n-space>
    </n-card>

    <!-- 对话白名单卡片 -->
    <n-card title="💬 对话白名单" size="small" :bordered="true">
      <template #header-extra>
        <n-text v-if="result" depth="3" style="font-size: 12px">
          共 {{ result.total_count }} 条
        </n-text>
      </template>

      <n-space vertical :size="10">
        <!-- 筛选区 -->
        <n-space :size="8" wrap align="center">
          <n-input-number
            v-model:value="filterChapter"
            :min="1"
            clearable
            placeholder="章节"
            style="width: 80px"
            size="small"
            @update:value="debouncedLoad"
          />
          <n-select
            v-model:value="filterSpeaker"
            :options="speakerOptions"
            placeholder="说话人"
            clearable
            filterable
            style="width: 120px"
            size="small"
            @update:value="debouncedLoad"
          />
          <n-input
            v-model:value="searchText"
            placeholder="搜索对话内容..."
            clearable
            size="small"
            style="width: 140px"
          />
          <n-button
            size="small"
            :loading="loading"
            @click="loadWhitelist"
          >
            刷新
          </n-button>
        </n-space>

        <!-- 对话列表 -->
        <n-spin :show="loading">
          <n-scrollbar style="max-height: 380px">
            <n-empty v-if="!result" description="加载中..." size="small" />
            <n-empty v-else-if="result.total_count === 0" description="暂无对话数据，生成章节后自动提取" size="small" />
            <n-empty v-else-if="filteredDialogues.length === 0" description="无匹配对话" size="small" />
            <n-space v-else vertical :size="6" style="padding-right: 4px">
              <n-card
                v-for="d in filteredDialogues"
                :key="d.dialogue_id"
                size="small"
                :bordered="true"
                class="dialogue-card"
                hoverable
              >
                <template #header>
                  <n-space align="center" :size="6">
                    <n-tag type="info" size="tiny" round>第{{ d.chapter }}章</n-tag>
                    <n-tag type="warning" size="tiny" round>{{ d.speaker }}</n-tag>
                  </n-space>
                </template>
                <n-text style="font-size: 13px; line-height: 1.6">{{ d.content }}</n-text>
              </n-card>
            </n-space>
          </n-scrollbar>
        </n-spin>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkbenchRefreshStore } from '../../stores/workbenchRefreshStore'
import { useMessage } from 'naive-ui'
import { sandboxApi } from '../../api/sandbox'
import type { DialogueWhitelistResponse, DialogueEntry, CharacterAnchor } from '../../api/sandbox'
import { bibleApi } from '../../api/bible'
import type { CharacterDTO } from '../../api/bible'

const props = defineProps<{ slug: string }>()
const message = useMessage()

// 状态
const loading = ref(false)
const charLoading = ref(false)
const result = ref<DialogueWhitelistResponse | null>(null)
const filterChapter = ref<number | null>(null)
const filterSpeaker = ref('')
const searchText = ref('')

const characters = ref<CharacterDTO[]>([])
const selectedCharacterId = ref<string | null>(null)
const anchor = ref<CharacterAnchor | null>(null)
const anchorLoading = ref(false)
const genLoading = ref(false)
const saveLoading = ref(false)
const editMental = ref('')
const editVerbal = ref('')
const editIdle = ref('')
const scenePrompt = ref('')
const generatedLine = ref('')

// 角色选项
const characterOptions = computed(() =>
  characters.value.map(c => ({ label: c.name || c.id, value: c.id }))
)

// 说话人选项（从已有对话中提取）
const speakerOptions = computed(() => {
  if (!result.value) return []
  const speakers = new Set<string>()
  result.value.dialogues.forEach(d => speakers.add(d.speaker))
  return Array.from(speakers).map(s => ({ label: s, value: s }))
})

// 过滤后的对话
const filteredDialogues = computed<DialogueEntry[]>(() => {
  if (!result.value) return []
  let list = result.value.dialogues
  
  // 章节筛选（已在 API 层处理，这里保留用于搜索）
  const kw = searchText.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(d =>
      d.content.toLowerCase().includes(kw) ||
      d.speaker.toLowerCase().includes(kw)
    )
  }
  return list
})

// 加载角色列表
async function loadCharacters() {
  charLoading.value = true
  try {
    characters.value = await bibleApi.listCharacters(props.slug)
  } catch {
    characters.value = []
  } finally {
    charLoading.value = false
  }
}

// 选择角色时自动载入锚点
async function onCharacterSelect(charId: string | null) {
  if (!charId) {
    anchor.value = null
    generatedLine.value = ''
    return
  }
  
  anchorLoading.value = true
  generatedLine.value = ''
  try {
    const a = await sandboxApi.getCharacterAnchor(props.slug, charId)
    anchor.value = a
    editMental.value = a.mental_state || ''
    editVerbal.value = a.verbal_tic || ''
    editIdle.value = a.idle_behavior || ''
  } catch {
    message.error('载入锚点失败')
    anchor.value = null
  } finally {
    anchorLoading.value = false
  }
}

// 保存锚点
async function saveAnchors() {
  const id = selectedCharacterId.value
  if (!id) return
  saveLoading.value = true
  try {
    await sandboxApi.patchCharacterAnchor(props.slug, id, {
      mental_state: editMental.value || 'NORMAL',
      verbal_tic: editVerbal.value || '',
      idle_behavior: editIdle.value || '',
    })
    message.success('已保存到 Bible')
    refreshStore.bumpDesk()
  } catch {
    message.error('保存失败')
  } finally {
    saveLoading.value = false
  }
}

// 生成对话
async function runGenerate() {
  const id = selectedCharacterId.value
  if (!id || !scenePrompt.value.trim()) return
  genLoading.value = true
  generatedLine.value = ''
  try {
    const res = await sandboxApi.generateDialogue({
      novel_id: props.slug,
      character_id: id,
      scene_prompt: scenePrompt.value.trim(),
      mental_state: editMental.value || undefined,
      verbal_tic: editVerbal.value || undefined,
      idle_behavior: editIdle.value || undefined,
    })
    generatedLine.value = res.dialogue
  } catch {
    message.error('生成失败')
  } finally {
    genLoading.value = false
  }
}

// 加载对话白名单
async function loadWhitelist() {
  loading.value = true
  try {
    result.value = await sandboxApi.getDialogueWhitelist(
      props.slug,
      filterChapter.value ?? undefined,
      filterSpeaker.value.trim() || undefined
    )
  } catch {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 防抖加载
let debounceTimer: ReturnType<typeof setTimeout> | null = null
function debouncedLoad() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    loadWhitelist()
  }, 300)
}

// 监听 slug 变化
watch(
  () => props.slug,
  () => {
    loadCharacters()
    loadWhitelist()
    anchor.value = null
    generatedLine.value = ''
  }
)

// 初始化
onMounted(() => {
  loadCharacters()
  loadWhitelist()
})

// 刷新监听
const refreshStore = useWorkbenchRefreshStore()
const { deskTick } = storeToRefs(refreshStore)
watch(deskTick, () => {
  loadCharacters()
  loadWhitelist()
})
</script>

<style scoped>
.sandbox-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 12px 16px;
  gap: 12px;
}

.anchor-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.anchor-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-color-3);
}

.generated-output {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.05), rgba(124, 58, 237, 0.08));
}

.dialogue-card {
  transition: all 0.2s ease;
}

.dialogue-card:hover {
  transform: translateX(4px);
}

.sandbox-panel :deep(.n-card) {
  border-radius: 10px;
}

.sandbox-panel :deep(.n-card__header) {
  padding: 12px 16px;
  font-weight: 700;
  font-size: 14px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.05), rgba(124, 58, 237, 0.08));
}

.sandbox-panel :deep(.n-collapse-item__header-main) {
  font-weight: 600;
}

.sandbox-panel :deep(.n-input),
.sandbox-panel :deep(.n-select),
.sandbox-panel :deep(.n-input-number) {
  border-radius: 6px;
}

.sandbox-panel :deep(.n-button) {
  border-radius: 6px;
}

.sandbox-panel :deep(.n-tag) {
  border-radius: 4px;
}

.sandbox-panel :deep(.n-empty) {
  padding: 20px 0;
}
</style>
