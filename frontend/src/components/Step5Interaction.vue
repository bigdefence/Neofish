<template>
  <div class="interaction-panel">
    <!-- Main Split Layout -->
    <div class="main-split-layout">
      <!-- LEFT PANEL: Report Style -->
      <div class="left-panel report-style" ref="leftPanel">
        <div v-if="reportOutline" class="report-content-wrapper">
          <!-- Report Header -->
          <div class="report-header-block">
            <div class="report-meta">
              <span class="report-tag">Prediction Report</span>
              <span class="report-id">ID: {{ reportId || 'REF-2024-X92' }}</span>
            </div>
            <h1 class="main-title">{{ reportOutline.title }}</h1>
            <p class="sub-title">{{ reportOutline.summary }}</p>
            <div class="header-divider"></div>
          </div>

          <!-- Sections List -->
          <div class="sections-list">
            <div 
              v-for="(section, idx) in reportOutline.sections" 
              :key="idx"
              class="report-section-item"
              :class="{ 
                'is-active': currentSectionIndex === idx + 1,
                'is-completed': isSectionCompleted(idx + 1),
                'is-pending': !isSectionCompleted(idx + 1) && currentSectionIndex !== idx + 1
              }"
            >
              <div class="section-header-row" @click="toggleSectionCollapse(idx)" :class="{ 'clickable': isSectionCompleted(idx + 1) }">
                <span class="section-number">{{ String(idx + 1).padStart(2, '0') }}</span>
                <h3 class="section-title">{{ section.title }}</h3>
                <svg 
                  v-if="isSectionCompleted(idx + 1)" 
                  class="collapse-icon" 
                  :class="{ 'is-collapsed': collapsedSections.has(idx) }"
                  viewBox="0 0 24 24" 
                  width="20" 
                  height="20" 
                  fill="none" 
                  stroke="currentColor" 
                  stroke-width="2"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
              
              <div class="section-body" v-show="!collapsedSections.has(idx)">
                <!-- Completed Content -->
                <div v-if="generatedSections[idx + 1]" class="generated-content" v-html="renderMarkdown(generatedSections[idx + 1])"></div>
                
                <!-- Loading State -->
                <div v-else-if="currentSectionIndex === idx + 1" class="loading-state">
                  <div class="loading-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <circle cx="12" cy="12" r="10" stroke-width="4" stroke="#E5E7EB"></circle>
                      <path d="M12 2a10 10 0 0 1 10 10" stroke-width="4" stroke="#4B5563" stroke-linecap="round"></path>
                    </svg>
                  </div>
                  <span class="loading-text">{{ section.title }} 생성 중...</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Waiting State -->
        <div v-if="!reportOutline" class="waiting-placeholder">
          <div class="waiting-animation">
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
          </div>
          <span class="waiting-text">Waiting for Report Agent...</span>
        </div>
      </div>

      <!-- RIGHT PANEL: Interaction Interface -->
      <div class="right-panel" ref="rightPanel">
        <!-- Unified Action Bar - Professional Design -->
        <div class="action-bar">
        <div class="action-bar-header">
          <svg class="action-bar-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <div class="action-bar-text">
            <span class="action-bar-title">Interactive Tools</span>
            <span class="action-bar-subtitle mono">{{ profiles.length }} agents available</span>
          </div>
        </div>
          <div class="action-bar-tabs">
            <button 
              class="tab-pill"
              :class="{ active: activeTab === 'chat' && chatTarget === 'report_agent' }"
              @click="selectReportAgentChat"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
              </svg>
              <span>Report Agent와 대화</span>
            </button>
            <div class="agent-dropdown" v-if="profiles.length > 0">
              <button 
                class="tab-pill agent-pill"
                :class="{ active: activeTab === 'chat' && chatTarget === 'agent' }"
                @click="toggleAgentDropdown"
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <span>{{ selectedAgent ? selectedAgent.username : '시뮬레이션 세계의 임의 개체와 대화' }}</span>
                <svg class="dropdown-arrow" :class="{ open: showAgentDropdown }" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
              <div v-if="showAgentDropdown" class="dropdown-menu">
                <div class="dropdown-header">대화 대상 선택</div>
                <div 
                  v-for="(agent, idx) in profiles" 
                  :key="idx"
                  class="dropdown-item"
                  @click="selectAgent(agent, idx)"
                >
                  <div class="agent-avatar">{{ (agent.username || 'A')[0] }}</div>
                  <div class="agent-info">
                    <span class="agent-name">{{ agent.username }}</span>
                    <span class="agent-role">{{ agent.profession || '직업 정보 없음' }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="tab-divider"></div>
            <button 
              class="tab-pill survey-pill"
              :class="{ active: activeTab === 'survey' }"
              @click="selectSurveyTab"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3L22 4"></path>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
              </svg>
              <span>시뮬레이션 세계에 설문 전송</span>
            </button>
            <div class="tab-divider"></div>
            <button 
              class="tab-pill podcast-pill"
              :class="{ active: activeTab === 'podcast' }"
              @click="selectPodcastTab"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
              <span>팟캐스트 생성</span>
            </button>
          </div>
        </div>

        <!-- Chat Mode -->
        <div v-if="activeTab === 'chat'" class="chat-container">

          <!-- Report Agent Tools Card -->
          <div v-if="chatTarget === 'report_agent'" class="report-agent-tools-card">
            <div class="tools-card-header">
              <div class="tools-card-avatar">R</div>
              <div class="tools-card-info">
                <div class="tools-card-name">Report Agent - Chat</div>
                <div class="tools-card-subtitle">보고서 생성 에이전트의 빠른 대화 버전입니다. 4가지 전문 도구를 호출할 수 있으며 Neofish 전체 메모리를 활용합니다.</div>
              </div>
              <button class="tools-card-toggle" @click="showToolsDetail = !showToolsDetail">
                <svg :class="{ 'is-expanded': showToolsDetail }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
            </div>
            <div v-if="showToolsDetail" class="tools-card-body">
              <div class="tools-grid">
                <div class="tool-item tool-purple">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.5V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.5A7 7 0 0 0 12 2z"></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">InsightForge 심층 원인 분석</div>
                    <div class="tool-desc">현실 시드 데이터와 시뮬레이션 상태를 정렬해 Global/Local Memory 기반의 시공간 원인 분석을 제공합니다.</div>
                  </div>
                </div>
                <div class="tool-item tool-blue">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"></circle>
                      <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">PanoramaSearch 전방위 추적</div>
                    <div class="tool-desc">그래프 기반 탐색으로 사건 확산 경로를 재구성하고 정보 흐름의 전체 토폴로지를 포착합니다.</div>
                  </div>
                </div>
                <div class="tool-item tool-orange">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">QuickSearch 빠른 검색</div>
                    <div class="tool-desc">GraphRAG 기반 즉시 조회 인터페이스로 인덱싱 효율을 높여 구체적인 노드 속성과 사실을 빠르게 추출합니다.</div>
                  </div>
                </div>
                <div class="tool-item tool-green">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                      <circle cx="9" cy="7" r="4"></circle>
                      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">InterviewSubAgent 가상 인터뷰</div>
                    <div class="tool-desc">자율 인터뷰 방식으로 시뮬레이션 개체와 병렬 다회 대화를 수행해 비정형 의견 데이터와 심리 상태를 수집합니다.</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Agent Profile Card -->
          <div v-if="chatTarget === 'agent' && selectedAgent" class="agent-profile-card">
            <div class="profile-card-header">
              <div class="profile-card-avatar">{{ (selectedAgent.username || 'A')[0] }}</div>
              <div class="profile-card-info">
                <div class="profile-card-name">{{ selectedAgent.username }}</div>
                <div class="profile-card-meta">
                  <span v-if="selectedAgent.name" class="profile-card-handle">@{{ selectedAgent.name }}</span>
                  <span class="profile-card-profession">{{ selectedAgent.profession || '직업 정보 없음' }}</span>
                </div>
              </div>
              <button class="profile-card-toggle" @click="showFullProfile = !showFullProfile">
                <svg :class="{ 'is-expanded': showFullProfile }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
            </div>
            <div v-if="showFullProfile && selectedAgent.bio" class="profile-card-body">
              <div class="profile-card-bio">
                <div class="profile-card-label">소개</div>
                <p>{{ selectedAgent.bio }}</p>
              </div>
            </div>
          </div>

          <!-- Chat Messages -->
          <div class="chat-messages" ref="chatMessages">
            <div v-if="chatHistory.length === 0" class="chat-empty">
              <div class="empty-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
              <p class="empty-text">
                {{ chatTarget === 'report_agent' ? 'Report Agent와 대화해 보고서 내용을 깊이 이해합니다.' : '시뮬레이션 개체와 대화해 관점을 파악합니다.' }}
              </p>
            </div>
            <div 
              v-for="(msg, idx) in chatHistory" 
              :key="idx"
              class="chat-message"
              :class="msg.role"
            >
              <div class="message-avatar">
                <span v-if="msg.role === 'user'">U</span>
                <span v-else>{{ msg.role === 'assistant' && chatTarget === 'report_agent' ? 'R' : (selectedAgent?.username?.[0] || 'A') }}</span>
              </div>
              <div class="message-content">
                <div class="message-header">
                  <span class="sender-name">
                    {{ msg.role === 'user' ? 'You' : (chatTarget === 'report_agent' ? 'Report Agent' : (selectedAgent?.username || 'Agent')) }}
                  </span>
                  <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
                </div>
                <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
              </div>
            </div>
            <div v-if="isSending" class="chat-message assistant">
              <div class="message-avatar">
                <span>{{ chatTarget === 'report_agent' ? 'R' : (selectedAgent?.username?.[0] || 'A') }}</span>
              </div>
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Chat Input -->
          <div class="chat-input-area">
            <textarea 
              v-model="chatInput"
              class="chat-input"
              placeholder="질문을 입력하세요..."
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="isSending || (!selectedAgent && chatTarget === 'agent')"
              rows="1"
              ref="chatInputRef"
            ></textarea>
            <button 
              class="send-btn"
              @click="sendMessage"
              :disabled="!chatInput.trim() || isSending || (!selectedAgent && chatTarget === 'agent')"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>

        <!-- Survey Mode -->
        <div v-if="activeTab === 'survey'" class="survey-container">
          <!-- Survey Setup -->
          <div class="survey-setup">
            <div class="setup-section">
              <div class="section-header">
                <span class="section-title">설문 대상 선택</span>
                <span class="selection-count">선택됨 {{ selectedAgents.size }} / {{ profiles.length }}</span>
              </div>
              <div class="agents-grid">
                <label 
                  v-for="(agent, idx) in profiles" 
                  :key="idx"
                  class="agent-checkbox"
                  :class="{ checked: selectedAgents.has(idx) }"
                >
                  <input 
                    type="checkbox" 
                    :checked="selectedAgents.has(idx)"
                    @change="toggleAgentSelection(idx)"
                  >
                  <div class="checkbox-avatar">{{ (agent.username || 'A')[0] }}</div>
                  <div class="checkbox-info">
                    <span class="checkbox-name">{{ agent.username }}</span>
                    <span class="checkbox-role">{{ agent.profession || '직업 정보 없음' }}</span>
                  </div>
                  <div class="checkbox-indicator">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                  </div>
                </label>
              </div>
              <div class="selection-actions">
                <button class="action-link" @click="selectAllAgents">전체 선택</button>
                <span class="action-divider">|</span>
                <button class="action-link" @click="clearAgentSelection">선택 해제</button>
              </div>
            </div>

            <div class="setup-section">
              <div class="section-header">
                <span class="section-title">설문 질문</span>
              </div>
              <textarea 
                v-model="surveyQuestion"
                class="survey-input"
                placeholder="선택된 대상에게 공통으로 물어볼 질문을 입력하세요..."
                rows="3"
              ></textarea>
            </div>

            <button 
              class="survey-submit-btn"
              :disabled="selectedAgents.size === 0 || !surveyQuestion.trim() || isSurveying"
              @click="submitSurvey"
            >
              <span v-if="isSurveying" class="loading-spinner"></span>
              <span v-else>설문 전송</span>
            </button>
          </div>

          <!-- Survey Results -->
          <div v-if="surveyResults.length > 0" class="survey-results">
            <div class="results-header">
              <span class="results-title">설문 결과</span>
              <span class="results-count">{{ surveyResults.length }}개 응답</span>
            </div>
            <div class="results-list">
              <div 
                v-for="(result, idx) in surveyResults" 
                :key="idx"
                class="result-card"
              >
                <div class="result-header">
                  <div class="result-avatar">{{ (result.agent_name || 'A')[0] }}</div>
                  <div class="result-info">
                    <span class="result-name">{{ result.agent_name }}</span>
                    <span class="result-role">{{ result.profession || '직업 정보 없음' }}</span>
                  </div>
                </div>
                <div class="result-question">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                  <span>{{ result.question }}</span>
                </div>
                <div class="result-answer" v-html="renderMarkdown(result.answer)"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Podcast Mode -->
        <div v-if="activeTab === 'podcast'" class="podcast-container">
          <div class="podcast-setup">
            <div class="setup-section">
              <div class="section-header">
                <span class="section-title">보고서 팟캐스트 변환</span>
              </div>
              <p class="section-desc">현재 완성된 분석 보고서를 기반으로, 두 명의 패널이 토론하는 팟캐스트를 생성합니다.</p>
            </div>
            
            <button 
              v-if="!podcastAudioUrl && !isGeneratingPodcast"
              class="podcast-submit-btn"
              @click="generatePodcastAudio"
            >
              <span>팟캐스트 생성 시작</span>
            </button>
            <div v-if="isGeneratingPodcast" class="podcast-generating-status">
              <div class="waiting-animation">
                <div class="waiting-ring"></div>
                <div class="waiting-ring"></div>
                <div class="waiting-ring"></div>
              </div>
              <span class="generating-text">{{ podcastStatusMessage }}</span>
            </div>
            
            <div v-if="podcastAudioUrl" class="podcast-player-section">
              <div class="player-header">
                <span class="player-title">생성 완료</span>
              </div>
              <audio controls :src="podcastAudioUrl" class="podcast-audio-element"></audio>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { chatWithReport, getReport, getAgentLog, generatePodcast, getPodcastStatus, getPodcastInfo } from '../api/report'
import { interviewAgents, getSimulationProfilesRealtime } from '../api/simulation'

const props = defineProps({
  reportId: String,
  simulationId: String
})

const emit = defineEmits(['add-log', 'update-status'])

// State
const activeTab = ref('chat')
const chatTarget = ref('report_agent')
const showAgentDropdown = ref(false)
const selectedAgent = ref(null)
const selectedAgentIndex = ref(null)
const showFullProfile = ref(true)
const showToolsDetail = ref(true)

// Chat State
const chatInput = ref('')
const chatHistory = ref([])
const chatHistoryCache = ref({}) // 모든 대화 기록 캐시: { 'report_agent': [], 'agent_0': [], 'agent_1': [], ... }
const isSending = ref(false)
const chatMessages = ref(null)
const chatInputRef = ref(null)

// Survey State
const selectedAgents = ref(new Set())
const surveyQuestion = ref('')
const surveyResults = ref([])
const isSurveying = ref(false)

// Podcast State
const podcastAudioUrl = ref(null)
const isGeneratingPodcast = ref(false)
const podcastStatusMessage = ref('')
let podcastInterval = null

// Report Data
const reportOutline = ref(null)
const generatedSections = ref({})
const collapsedSections = ref(new Set())
const currentSectionIndex = ref(null)
const profiles = ref([])

// Helper Methods
const isSectionCompleted = (sectionIndex) => {
  return !!generatedSections.value[sectionIndex]
}

// Refs
const leftPanel = ref(null)
const rightPanel = ref(null)

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

const toggleSectionCollapse = (idx) => {
  if (!generatedSections.value[idx + 1]) return
  const newSet = new Set(collapsedSections.value)
  if (newSet.has(idx)) {
    newSet.delete(idx)
  } else {
    newSet.add(idx)
  }
  collapsedSections.value = newSet
}

const selectChatTarget = (target) => {
  chatTarget.value = target
  if (target === 'report_agent') {
    showAgentDropdown.value = false
  }
}

// 현재 대화 기록을 캐시에 저장
const saveChatHistory = () => {
  if (chatHistory.value.length === 0) return
  
  if (chatTarget.value === 'report_agent') {
    chatHistoryCache.value['report_agent'] = [...chatHistory.value]
  } else if (selectedAgentIndex.value !== null) {
    chatHistoryCache.value[`agent_${selectedAgentIndex.value}`] = [...chatHistory.value]
  }
}

const selectReportAgentChat = () => {
  // 현재 대화 기록 저장
  saveChatHistory()
  
  activeTab.value = 'chat'
  chatTarget.value = 'report_agent'
  selectedAgent.value = null
  selectedAgentIndex.value = null
  showAgentDropdown.value = false
  
  // Report Agent 대화 기록 복원
  chatHistory.value = chatHistoryCache.value['report_agent'] || []
}

const selectSurveyTab = () => {
  activeTab.value = 'survey'
  selectedAgent.value = null
  selectedAgentIndex.value = null
  showAgentDropdown.value = false
}

const selectPodcastTab = () => {
  activeTab.value = 'podcast'
  selectedAgent.value = null
  selectedAgentIndex.value = null
  showAgentDropdown.value = false
  checkPodcastInfo()
}

const checkPodcastInfo = async () => {
  if (!props.reportId) return
  try {
    const res = await getPodcastInfo(props.reportId)
    if (res.success && res.data.has_podcast) {
      podcastAudioUrl.value = res.data.audio_url
    }
  } catch(e) {
    console.warn("Failed to check podcast info", e)
  }
}

const generatePodcastAudio = async () => {
  if (!props.reportId) return
  isGeneratingPodcast.value = true
  podcastStatusMessage.value = "팟캐스트 생성 요청 중..."
  try {
    addLog('팟캐스트 생성 요청 시작')
    const res = await generatePodcast(props.reportId)
    if (res.success && res.data) {
      if (res.data.already_exists) {
        checkPodcastInfo()
        isGeneratingPodcast.value = false
        return
      }
      const taskId = res.data.task_id
      pollPodcastStatus(taskId)
    }
  } catch(e) {
    isGeneratingPodcast.value = false
    addLog(`팟캐스트 생성 요청 실패: ${e.message}`)
    podcastStatusMessage.value = "생성 오류 발생"
  }
}

const pollPodcastStatus = (taskId) => {
  podcastInterval = setInterval(async () => {
    try {
      const res = await getPodcastStatus(taskId)
      if (res.success && res.data) {
        podcastStatusMessage.value = res.data.message || "생성 중..."
        if (res.data.status === 'completed') {
          clearInterval(podcastInterval)
          podcastInterval = null
          isGeneratingPodcast.value = false
          checkPodcastInfo()
          addLog('팟캐스트 생성 완료')
        } else if (res.data.status === 'failed') {
          clearInterval(podcastInterval)
          podcastInterval = null
          isGeneratingPodcast.value = false
          podcastStatusMessage.value = "생성 실패"
          addLog(`팟캐스트 생성 실패: ${res.data.error || '알 수 없는 오류'}`)
        }
      }
    } catch(e) {
      console.warn("Polling error", e)
    }
  }, 2000)
}

onUnmounted(() => {
  if (podcastInterval) clearInterval(podcastInterval)
})

const toggleAgentDropdown = () => {
  showAgentDropdown.value = !showAgentDropdown.value
  if (showAgentDropdown.value) {
    activeTab.value = 'chat'
    chatTarget.value = 'agent'
  }
}

const selectAgent = (agent, idx) => {
  // 현재 대화 기록 저장
  saveChatHistory()
  
  selectedAgent.value = agent
  selectedAgentIndex.value = idx
  chatTarget.value = 'agent'
  showAgentDropdown.value = false
  
  // 해당 Agent 대화 기록 복원
  chatHistory.value = chatHistoryCache.value[`agent_${idx}`] || []
  addLog(`대화 대상 선택: ${agent.username}`)
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit'
    })
  } catch {
    return ''
  }
}

const renderMarkdown = (content) => {
  if (!content) return ''
  
  let processedContent = content.replace(/^##\s+.+\n+/, '')
  let html = processedContent.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  html = html.replace(/^#### (.+)$/gm, '<h5 class="md-h5">$1</h5>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')
  html = html.replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')
  
  // 목록 처리 - 하위 목록 지원
  html = html.replace(/^(\s*)- (.+)$/gm, (match, indent, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-li" data-level="${level}">${text}</li>`
  })
  html = html.replace(/^(\s*)(\d+)\. (.+)$/gm, (match, indent, num, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-oli" data-level="${level}">${text}</li>`
  })
  
  // 순서 없는 목록 래핑
  html = html.replace(/(<li class="md-li"[^>]*>.*?<\/li>\s*)+/g, '<ul class="md-ul">$&</ul>')
  // 순서 있는 목록 래핑
  html = html.replace(/(<li class="md-oli"[^>]*>.*?<\/li>\s*)+/g, '<ol class="md-ol">$&</ol>')
  
  // 목록 항목 사이 공백 정리
  html = html.replace(/<\/li>\s+<li/g, '</li><li')
  // 목록 시작 태그 뒤 공백 정리
  html = html.replace(/<ul class="md-ul">\s+/g, '<ul class="md-ul">')
  html = html.replace(/<ol class="md-ol">\s+/g, '<ol class="md-ol">')
  // 목록 종료 태그 앞 공백 정리
  html = html.replace(/\s+<\/ul>/g, '</ul>')
  html = html.replace(/\s+<\/ol>/g, '</ol>')
  
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/_(.+?)_/g, '<em>$1</em>')
  html = html.replace(/^---$/gm, '<hr class="md-hr">')
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = html.replace(/\n/g, '<br>')
  html = '<p class="md-p">' + html + '</p>'
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/<p class="md-p">(<h[2-5])/g, '$1')
  html = html.replace(/(<\/h[2-5]>)<\/p>/g, '$1')
  html = html.replace(/<p class="md-p">(<ul|<ol|<blockquote|<pre|<hr)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, '$1')
  // 블록 요소 앞뒤 <br> 정리
  html = html.replace(/<br>\s*(<ul|<ol|<blockquote)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>)\s*<br>/g, '$1')
  // 불필요한 빈 줄로 생긴 <p><br> + 블록 요소 패턴 정리
  html = html.replace(/<p class="md-p">(<br>\s*)+(<ul|<ol|<blockquote|<pre|<hr)/g, '$2')
  // 연속된 <br> 정리
  html = html.replace(/(<br>\s*){2,}/g, '<br>')
  // 블록 요소 뒤 단락 시작 태그 앞 <br> 정리
  html = html.replace(/(<\/ol>|<\/ul>|<\/blockquote>)<br>(<p|<div)/g, '$1$2')

  // 비연속 ordered list 번호 보정: 단일 <ol> 사이 문단이 있어도 번호가 이어지도록 처리
  const tokens = html.split(/(<ol class="md-ol">(?:<li class="md-oli"[^>]*>[\s\S]*?<\/li>)+<\/ol>)/g)
  let olCounter = 0
  let inSequence = false
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].startsWith('<ol class="md-ol">')) {
      const liCount = (tokens[i].match(/<li class="md-oli"/g) || []).length
      if (liCount === 1) {
        olCounter++
        if (olCounter > 1) {
          tokens[i] = tokens[i].replace('<ol class="md-ol">', `<ol class="md-ol" start="${olCounter}">`)
        }
        inSequence = true
      } else {
        olCounter = 0
        inSequence = false
      }
    } else if (inSequence) {
      if (/<h[2-5]/.test(tokens[i])) {
        olCounter = 0
        inSequence = false
      }
    }
  }
  html = tokens.join('')

  return html
}

// Chat Methods
const sendMessage = async () => {
  if (!chatInput.value.trim() || isSending.value) return
  
  const message = chatInput.value.trim()
  chatInput.value = ''
  
  // Add user message
  chatHistory.value.push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  })
  
  scrollToBottom()
  isSending.value = true
  
  try {
    if (chatTarget.value === 'report_agent') {
      await sendToReportAgent(message)
    } else {
      await sendToAgent(message)
    }
  } catch (err) {
    addLog(`전송 실패: ${err.message}`)
    chatHistory.value.push({
      role: 'assistant',
      content: `죄송합니다. 오류가 발생했습니다: ${err.message}`,
      timestamp: new Date().toISOString()
    })
  } finally {
    isSending.value = false
    scrollToBottom()
    // 대화 기록을 캐시에 자동 저장
    saveChatHistory()
  }
}

const sendToReportAgent = async (message) => {
  addLog(`Report Agent로 전송: ${message.substring(0, 50)}...`)
  
  // Build chat history for API
  const historyForApi = chatHistory.value
    .filter(msg => msg.role !== 'user' || msg.content !== message)
    .slice(-10) // Keep last 10 messages
    .map(msg => ({
      role: msg.role,
      content: msg.content
    }))
  
  const res = await chatWithReport({
    simulation_id: props.simulationId,
    message: message,
    chat_history: historyForApi
  })
  
  if (res.success && res.data) {
    chatHistory.value.push({
      role: 'assistant',
      content: res.data.response || res.data.answer || '응답 없음',
      timestamp: new Date().toISOString()
    })
    addLog('Report Agent 응답 수신')
  } else {
    throw new Error(res.error || '요청 실패')
  }
}

const sendToAgent = async (message) => {
  if (!selectedAgent.value || selectedAgentIndex.value === null) {
    throw new Error('먼저 시뮬레이션 개체를 선택해 주세요.')
  }
  
  addLog(`${selectedAgent.value.username}에게 전송: ${message.substring(0, 50)}...`)
  
  // Build prompt with chat history
  let prompt = message
  if (chatHistory.value.length > 1) {
    const historyContext = chatHistory.value
      .filter(msg => msg.content !== message)
      .slice(-6)
      .map(msg => `${msg.role === 'user' ? '질문자' : '당신'}: ${msg.content}`)
      .join('\n')
    prompt = `아래는 이전 대화 내용입니다:\n${historyContext}\n\n새 질문은 다음과 같습니다: ${message}`
  }
  
  const res = await interviewAgents({
    simulation_id: props.simulationId,
    interviews: [{
      agent_id: selectedAgentIndex.value,
      prompt: prompt
    }]
  })
  
  if (res.success && res.data) {
    // 데이터 경로: res.data.result.results (객체 딕셔너리)
    // 형식: {"twitter_0": {...}, "reddit_0": {...}} 또는 단일 플랫폼 {"reddit_0": {...}}
    const resultData = res.data.result || res.data
    const resultsDict = resultData.results || resultData
    
    // 객체 딕셔너리를 배열로 변환하고 reddit 응답을 우선 사용
    let responseContent = null
    const agentId = selectedAgentIndex.value
    
    if (typeof resultsDict === 'object' && !Array.isArray(resultsDict)) {
      // reddit 응답 우선, 없으면 twitter
      const redditKey = `reddit_${agentId}`
      const twitterKey = `twitter_${agentId}`
      const agentResult = resultsDict[redditKey] || resultsDict[twitterKey] || Object.values(resultsDict)[0]
      if (agentResult) {
        responseContent = agentResult.response || agentResult.answer
      }
    } else if (Array.isArray(resultsDict) && resultsDict.length > 0) {
      // 배열 형식 호환 처리
      responseContent = resultsDict[0].response || resultsDict[0].answer
    }
    
    if (responseContent) {
      chatHistory.value.push({
        role: 'assistant',
        content: responseContent,
        timestamp: new Date().toISOString()
      })
      addLog(`${selectedAgent.value.username} 응답 수신`)
    } else {
      throw new Error('응답 데이터가 없습니다.')
    }
  } else {
    throw new Error(res.error || '요청 실패')
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessages.value) {
      chatMessages.value.scrollTop = chatMessages.value.scrollHeight
    }
  })
}

// Survey Methods
const toggleAgentSelection = (idx) => {
  const newSet = new Set(selectedAgents.value)
  if (newSet.has(idx)) {
    newSet.delete(idx)
  } else {
    newSet.add(idx)
  }
  selectedAgents.value = newSet
}

const selectAllAgents = () => {
  const newSet = new Set()
  profiles.value.forEach((_, idx) => newSet.add(idx))
  selectedAgents.value = newSet
}

const clearAgentSelection = () => {
  selectedAgents.value = new Set()
}

const submitSurvey = async () => {
  if (selectedAgents.value.size === 0 || !surveyQuestion.value.trim()) return
  
  isSurveying.value = true
  addLog(`${selectedAgents.value.size}명의 대상에게 설문 전송 중...`)
  
  try {
    const interviews = Array.from(selectedAgents.value).map(idx => ({
      agent_id: idx,
      prompt: surveyQuestion.value.trim()
    }))
    
    const res = await interviewAgents({
      simulation_id: props.simulationId,
      interviews: interviews
    })
    
    if (res.success && res.data) {
      // 데이터 경로: res.data.result.results (객체 딕셔너리)
      // 형식: {"twitter_0": {...}, "reddit_0": {...}, "twitter_1": {...}, ...}
      const resultData = res.data.result || res.data
      const resultsDict = resultData.results || resultData
      
      // 객체 딕셔너리를 배열 형식으로 변환
      const surveyResultsList = []
      
      for (const interview of interviews) {
        const agentIdx = interview.agent_id
        const agent = profiles.value[agentIdx]
        
        // reddit 응답 우선, 없으면 twitter
        let responseContent = '응답 없음'
        
        if (typeof resultsDict === 'object' && !Array.isArray(resultsDict)) {
          const redditKey = `reddit_${agentIdx}`
          const twitterKey = `twitter_${agentIdx}`
          const agentResult = resultsDict[redditKey] || resultsDict[twitterKey]
          if (agentResult) {
            responseContent = agentResult.response || agentResult.answer || '응답 없음'
          }
        } else if (Array.isArray(resultsDict)) {
          // 배열 형식 호환 처리
          const matchedResult = resultsDict.find(r => r.agent_id === agentIdx)
          if (matchedResult) {
            responseContent = matchedResult.response || matchedResult.answer || '응답 없음'
          }
        }
        
        surveyResultsList.push({
          agent_id: agentIdx,
          agent_name: agent?.username || `Agent ${agentIdx}`,
          profession: agent?.profession,
          question: surveyQuestion.value.trim(),
          answer: responseContent
        })
      }
      
      surveyResults.value = surveyResultsList
      addLog(`${surveyResults.value.length}개 응답 수신`)
    } else {
      throw new Error(res.error || '요청 실패')
    }
  } catch (err) {
    addLog(`설문 전송 실패: ${err.message}`)
  } finally {
    isSurveying.value = false
  }
}

// Load Report Data
const loadReportData = async () => {
  if (!props.reportId) return
  
  try {
    addLog(`보고서 데이터 로드: ${props.reportId}`)
    
    // Get report info
    const reportRes = await getReport(props.reportId)
    if (reportRes.success && reportRes.data) {
      // Load agent logs to get report outline and sections
      await loadAgentLogs()
    }
  } catch (err) {
    addLog(`보고서 로드 실패: ${err.message}`)
  }
}

const loadAgentLogs = async () => {
  if (!props.reportId) return
  
  try {
    const res = await getAgentLog(props.reportId, 0)
    if (res.success && res.data) {
      const logs = res.data.logs || []
      
      logs.forEach(log => {
        if (log.action === 'planning_complete' && log.details?.outline) {
          reportOutline.value = log.details.outline
        }
        
        if (log.action === 'section_complete' && log.section_index < 100 && log.details?.content) {
          generatedSections.value[log.section_index] = log.details.content
        }
      })
      
      addLog('보고서 데이터 로드 완료')
    }
  } catch (err) {
    addLog(`보고서 로그 로드 실패: ${err.message}`)
  }
}

const loadProfiles = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId, 'reddit')
    if (res.success && res.data) {
      profiles.value = res.data.profiles || []
      addLog(`${profiles.value.length}명의 시뮬레이션 개체를 불러왔습니다.`)
    }
  } catch (err) {
    addLog(`시뮬레이션 개체 로드 실패: ${err.message}`)
  }
}

// Click outside to close dropdown
const handleClickOutside = (e) => {
  const dropdown = document.querySelector('.agent-dropdown')
  if (dropdown && !dropdown.contains(e.target)) {
    showAgentDropdown.value = false
  }
}

// Lifecycle
onMounted(() => {
  addLog('Step5 심화 상호작용 초기화')
  loadReportData()
  loadProfiles()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(() => props.reportId, (newId) => {
  if (newId) {
    loadReportData()
  }
}, { immediate: true })

watch(() => props.simulationId, (newId) => {
  if (newId) {
    loadProfiles()
  }
}, { immediate: true })
</script>

<style scoped>
.interaction-panel {
  height: 100%; display: flex; flex-direction: column; background: var(--bg-color);
  font-family: var(--font-body); overflow: hidden; color: var(--foreground);
}

.mono { font-family: var(--font-accent); }

.main-split-layout {
  flex: 1; display: flex; overflow: hidden; border-top: 1px solid var(--glass-border);
}

.left-panel.report-style {
  width: 45%; min-width: 450px; background: var(--glass-bg); border-right: 1px solid var(--glass-border);
  overflow-y: auto; display: flex; flex-direction: column; padding: 30px 50px 60px 50px;
  backdrop-filter: blur(10px);
}

.left-panel::-webkit-scrollbar { width: 6px; }
.left-panel::-webkit-scrollbar-track { background: transparent; }
.left-panel::-webkit-scrollbar-thumb { background: rgba(0, 240, 255, 0.2); border-radius: 3px; border: 1px solid var(--accent); }
.left-panel::-webkit-scrollbar-thumb:hover { background: var(--accent); box-shadow: var(--accent-glow); }

.report-content-wrapper { max-width: 800px; margin: 0 auto; width: 100%; }
.report-header-block { margin-bottom: 30px; }
.report-meta { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
.report-tag {
  background: rgba(0, 240, 255, 0.1); color: var(--accent); border: 1px solid var(--accent);
  font-family: var(--font-accent); font-size: 11px; font-weight: 700; padding: 4px 8px;
  letter-spacing: 0.05em; text-transform: uppercase; box-shadow: 0 0 10px rgba(0, 240, 255, 0.2);
}
.report-id { font-family: var(--font-accent); font-size: 11px; color: var(--text-muted); font-weight: 500; letter-spacing: 0.02em; }
.main-title {
  font-family: var(--font-heading); font-size: 32px; font-weight: 700; color: var(--foreground);
  line-height: 1.2; margin: 0 0 16px 0; letter-spacing: 1px; text-transform: uppercase;
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
}
.sub-title { font-family: var(--font-body); font-size: 14px; color: var(--text-muted); line-height: 1.6; margin: 0 0 30px 0; }
.header-divider { height: 1px; background: var(--glass-border); width: 100%; box-shadow: 0 0 10px rgba(0, 240, 255, 0.1); }

.sections-list { display: flex; flex-direction: column; gap: 32px; }
.report-section-item { display: flex; flex-direction: column; gap: 12px; }
.section-header-row {
  display: flex; align-items: baseline; gap: 12px; transition: all 0.2s ease;
  padding: 8px 12px; margin: -8px -12px; border-radius: 4px; border-left: 2px solid transparent;
}
.section-header-row.clickable { cursor: pointer; }
.section-header-row.clickable:hover { background: rgba(0, 240, 255, 0.05); border-left-color: var(--accent); }
.collapse-icon { margin-left: auto; color: var(--accent); transition: transform 0.3s ease; flex-shrink: 0; align-self: center; filter: drop-shadow(0 0 5px var(--accent)); }
.collapse-icon.is-collapsed { transform: rotate(-90deg); }
.section-number { font-family: var(--font-accent); font-size: 16px; color: var(--text-muted); font-weight: 500; transition: color 0.3s ease; }
.section-title { font-family: var(--font-heading); font-size: 20px; font-weight: 600; color: var(--foreground); margin: 0; transition: color 0.3s ease; letter-spacing: 0.5px; }

.report-section-item.is-pending .section-number { color: #555; }
.report-section-item.is-pending .section-title { color: #777; }
.report-section-item.is-active .section-number, .report-section-item.is-completed .section-number { color: var(--accent); text-shadow: var(--accent-glow); }
.report-section-item.is-active .section-title, .report-section-item.is-completed .section-title { color: var(--accent); text-shadow: 0 0 8px rgba(0, 240, 255, 0.3); }

.section-body { padding-left: 28px; border-left: 1px dashed var(--card-border); margin-left: 8px; overflow: hidden; }

.generated-content { font-family: var(--font-body); font-size: 14px; line-height: 1.8; color: var(--foreground); }
.generated-content :deep(p) { margin-bottom: 1em; }
.generated-content :deep(.md-h2), .generated-content :deep(.md-h3), .generated-content :deep(.md-h4) {
  font-family: var(--font-heading); color: var(--accent); margin-top: 1.5em; margin-bottom: 0.8em; font-weight: 600; letter-spacing: 1px;
}
.generated-content :deep(.md-h2) { font-size: 18px; border-bottom: 1px solid var(--glass-border); padding-bottom: 8px; }
.generated-content :deep(.md-h3) { font-size: 16px; color: var(--secondary); text-shadow: var(--secondary-glow); }
.generated-content :deep(.md-h4) { font-size: 14px; color: #fff; }
.generated-content :deep(.md-ul), .generated-content :deep(.md-ol) { padding-left: 20px; margin-bottom: 1em; }
.generated-content :deep(.md-li) { margin-bottom: 0.5em; }
.generated-content :deep(.md-quote) {
  border-left: 3px solid var(--accent); padding-left: 16px; margin: 1.5em 0; color: var(--text-muted); font-style: italic;
  font-family: var(--font-body); background: rgba(0, 240, 255, 0.05); padding: 10px 16px; border-radius: 0 4px 4px 0;
}
.generated-content :deep(.code-block) {
  background: var(--bg-color); padding: 12px; border-radius: 4px; font-family: var(--font-body); font-size: 12px;
  overflow-x: auto; margin: 1em 0; border: 1px solid var(--card-border); color: var(--secondary);
}
.generated-content :deep(strong) { font-weight: 600; color: #fff; text-shadow: 0 0 5px rgba(255, 255, 255, 0.3); }

.loading-state { display: flex; align-items: center; gap: 10px; color: var(--accent); font-size: 14px; margin-top: 4px; }
.loading-icon { width: 18px; height: 18px; animation: spin 1s linear infinite; display: flex; align-items: center; justify-content: center; }
.loading-text { font-family: var(--font-accent); font-size: 14px; color: var(--accent); text-shadow: var(--accent-glow); }
@keyframes spin { to { transform: rotate(360deg); } }

.waiting-placeholder { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; padding: 40px; color: var(--text-muted); }
.waiting-animation { position: relative; width: 48px; height: 48px; }
.waiting-ring { position: absolute; width: 100%; height: 100%; border: 2px solid var(--accent); border-radius: 50%; animation: ripple 2s cubic-bezier(0.4, 0, 0.2, 1) infinite; box-shadow: var(--accent-glow); }
.waiting-ring:nth-child(2) { animation-delay: 0.4s; }
.waiting-ring:nth-child(3) { animation-delay: 0.8s; }
@keyframes ripple { 0% { transform: scale(0.5); opacity: 1; } 100% { transform: scale(2); opacity: 0; } }
.waiting-text { font-family: var(--font-accent); font-size: 14px; color: var(--accent); text-shadow: var(--accent-glow); }

.right-panel { flex: 1; display: flex; flex-direction: column; background: var(--bg-color-alpha); overflow: hidden; }

.action-bar { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-bottom: 1px solid var(--glass-border); background: var(--glass-bg); backdrop-filter: blur(10px); gap: 16px; }
.action-bar-header { display: flex; align-items: center; gap: 12px; min-width: 160px; }
.action-bar-icon { color: var(--accent); flex-shrink: 0; filter: drop-shadow(0 0 5px var(--accent)); }
.action-bar-text { display: flex; flex-direction: column; gap: 2px; }
.action-bar-title { font-family: var(--font-heading); font-size: 14px; font-weight: 600; color: var(--foreground); letter-spacing: 1px; text-transform: uppercase; }
.action-bar-subtitle { font-family: var(--font-accent); font-size: 11px; color: var(--accent); }

.action-bar-tabs { display: flex; align-items: center; gap: 6px; flex: 1; justify-content: flex-end; }
.tab-pill {
  display: flex; align-items: center; gap: 6px; padding: 8px 14px; font-family: var(--font-accent); font-size: 12px;
  color: var(--text-muted); background: transparent; border: 1px solid var(--card-border); border-radius: 4px;
  cursor: pointer; transition: all 0.2s ease; text-transform: uppercase;
}
.tab-pill:hover { background: rgba(0, 240, 255, 0.1); color: var(--accent); border-color: var(--accent); }
.tab-pill.active { background: rgba(0, 240, 255, 0.15); color: var(--accent); border-color: var(--accent); box-shadow: inset 0 0 10px rgba(0, 240, 255, 0.2); text-shadow: var(--accent-glow); }
.tab-pill svg { flex-shrink: 0; opacity: 0.8; }
.tab-pill.active svg { opacity: 1; filter: drop-shadow(0 0 3px var(--accent)); }
.tab-divider { width: 1px; height: 24px; background: var(--card-border); margin: 0 6px; }

.agent-pill { width: 200px; justify-content: space-between; }
.agent-pill span { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: left; }
.survey-pill { color: var(--secondary); border-color: var(--card-border); }
.survey-pill:hover { background: rgba(168, 85, 247, 0.1); color: var(--secondary); border-color: var(--secondary); }
.survey-pill.active { background: rgba(168, 85, 247, 0.15); color: var(--secondary); border-color: var(--secondary); box-shadow: inset 0 0 10px rgba(168, 85, 247, 0.2); text-shadow: var(--secondary-glow); }

.agent-dropdown { position: relative; }
.dropdown-arrow { margin-left: 4px; transition: transform 0.2s ease; opacity: 0.6; }
.dropdown-arrow.open { transform: rotate(180deg); opacity: 1; }
.dropdown-menu {
  position: absolute; top: calc(100% + 6px); left: 50%; transform: translateX(-50%); min-width: 240px;
  background: rgba(10, 10, 15, 0.95); border: 1px solid var(--accent); border-radius: 4px; box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
  backdrop-filter: blur(10px); max-height: 320px; overflow-y: auto; z-index: 100;
}
.dropdown-header { padding: 12px 16px 8px; font-family: var(--font-accent); font-size: 11px; color: var(--accent); text-transform: uppercase; border-bottom: 1px solid var(--card-border); }
.dropdown-item { display: flex; align-items: center; gap: 12px; padding: 10px 16px; cursor: pointer; transition: all 0.15s ease; border-left: 2px solid transparent; }
.dropdown-item:hover { background: rgba(0, 240, 255, 0.1); border-left-color: var(--accent); }
.agent-avatar {
  width: 32px; height: 32px; min-width: 32px; min-height: 32px; background: rgba(0, 240, 255, 0.1); border: 1px solid var(--accent);
  color: var(--accent); border-radius: 4px; display: flex; align-items: center; justify-content: center; font-family: var(--font-heading);
  font-size: 12px; font-weight: 700; flex-shrink: 0; box-shadow: 0 0 10px rgba(0, 240, 255, 0.2);
}
.agent-info { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.agent-name { font-family: var(--font-heading); font-size: 13px; color: var(--foreground); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.agent-role { font-family: var(--font-accent); font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.chat-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: transparent; }

.report-agent-tools-card { border-bottom: 1px solid var(--glass-border); background: var(--card); }
.tools-card-header { display: flex; align-items: center; gap: 12px; padding: 14px 20px; }
.tools-card-avatar {
  width: 44px; height: 44px; min-width: 44px; min-height: 44px; background: rgba(0, 240, 255, 0.1); color: var(--accent);
  border: 1px solid var(--accent); border-radius: 4px; display: flex; align-items: center; justify-content: center;
  font-family: var(--font-heading); font-size: 18px; font-weight: 700; flex-shrink: 0; box-shadow: var(--accent-glow); text-shadow: var(--accent-glow);
}
.tools-card-info { flex: 1; min-width: 0; }
.tools-card-name { font-family: var(--font-heading); font-size: 15px; font-weight: 600; color: var(--foreground); margin-bottom: 2px; letter-spacing: 1px; }
.tools-card-subtitle { font-family: var(--font-body); font-size: 12px; color: var(--text-muted); }
.tools-card-toggle {
  width: 28px; height: 28px; background: transparent; border: 1px solid var(--card-border); border-radius: 4px;
  cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--accent); transition: all 0.2s ease; flex-shrink: 0;
}
.tools-card-toggle:hover { background: rgba(0, 240, 255, 0.1); border-color: var(--accent); box-shadow: var(--accent-glow); }
.tools-card-toggle svg { transition: transform 0.3s ease; }
.tools-card-toggle svg.is-expanded { transform: rotate(180deg); }
.tools-card-body { padding: 0 20px 16px 20px; }
.tools-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.tool-item {
  display: flex; gap: 10px; padding: 12px; background: rgba(10, 10, 15, 0.5); border-radius: 4px;
  border: 1px solid var(--card-border); transition: all 0.2s ease;
}
.tool-item:hover { border-color: var(--accent); transform: translateY(-2px); box-shadow: inset 0 0 15px rgba(0, 240, 255, 0.05); }

.tool-icon-wrapper { width: 32px; height: 32px; min-width: 32px; border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.tool-purple .tool-icon-wrapper { background: rgba(168, 85, 247, 0.1); color: var(--secondary); border: 1px solid var(--secondary); box-shadow: var(--secondary-glow); }
.tool-blue .tool-icon-wrapper { background: rgba(0, 240, 255, 0.1); color: var(--accent); border: 1px solid var(--accent); box-shadow: var(--accent-glow); }
.tool-orange .tool-icon-wrapper { background: rgba(255, 42, 42, 0.1); color: var(--warning); border: 1px solid var(--warning); box-shadow: 0 0 10px rgba(255, 42, 42, 0.5); }
.tool-green .tool-icon-wrapper { background: rgba(34, 197, 94, 0.1); color: #22C55E; border: 1px solid #22C55E; box-shadow: 0 0 10px rgba(34, 197, 94, 0.5); }
.tool-content { flex: 1; min-width: 0; }
.tool-name { font-family: var(--font-accent); font-size: 13px; font-weight: 600; color: var(--foreground); margin-bottom: 4px; }
.tool-desc { font-family: var(--font-body); font-size: 11px; color: var(--text-muted); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.agent-profile-card { border-bottom: 1px solid var(--glass-border); background: var(--card); }
.profile-card-header { display: flex; align-items: center; gap: 12px; padding: 14px 20px; }
.profile-card-avatar {
  width: 44px; height: 44px; min-width: 44px; min-height: 44px; background: rgba(168, 85, 247, 0.1); color: var(--secondary);
  border: 1px solid var(--secondary); border-radius: 4px; display: flex; align-items: center; justify-content: center;
  font-family: var(--font-heading); font-size: 18px; font-weight: 700; box-shadow: var(--secondary-glow);
}
.profile-card-info { flex: 1; min-width: 0; }
.profile-card-name { font-family: var(--font-heading); font-size: 15px; font-weight: 600; color: var(--foreground); margin-bottom: 2px; }
.profile-card-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; font-family: var(--font-accent); color: var(--text-muted); }
.profile-card-handle { color: var(--accent); }
.profile-card-profession { padding: 2px 8px; background: rgba(0, 240, 255, 0.1); border: 1px solid var(--accent); color: var(--accent); border-radius: 2px; font-size: 10px; }
.profile-card-toggle { width: 28px; height: 28px; background: transparent; border: 1px solid var(--card-border); border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--secondary); transition: all 0.2s ease; flex-shrink: 0; }
.profile-card-toggle:hover { background: rgba(168, 85, 247, 0.1); border-color: var(--secondary); box-shadow: var(--secondary-glow); }
.profile-card-toggle svg { transition: transform 0.3s ease; }
.profile-card-toggle svg.is-expanded { transform: rotate(180deg); }
.profile-card-body { padding: 0 20px 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.profile-card-label { font-family: var(--font-accent); font-size: 11px; color: var(--secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; text-shadow: var(--secondary-glow); }
.profile-card-bio { background: rgba(10, 10, 15, 0.5); padding: 12px 14px; border-radius: 4px; border: 1px dashed var(--secondary); }
.profile-card-bio p { margin: 0; font-size: 13px; line-height: 1.6; color: var(--foreground); font-family: var(--font-body); }

.chat-messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 24px; }
.chat-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: var(--accent); font-family: var(--font-accent); opacity: 0.5; }
.empty-icon { opacity: 0.8; filter: drop-shadow(0 0 5px var(--accent)); }
.empty-text { font-size: 14px; text-align: center; max-width: 280px; line-height: 1.6; }
.chat-message { display: flex; gap: 12px; }
.chat-message.user { flex-direction: row-reverse; }

.message-avatar {
  width: 36px; height: 36px; min-width: 36px; min-height: 36px; border-radius: 4px; display: flex; align-items: center;
  justify-content: center; font-family: var(--font-heading); font-size: 14px; font-weight: 700; flex-shrink: 0;
}
.chat-message.user .message-avatar { background: rgba(0, 240, 255, 0.1); color: var(--accent); border: 1px solid var(--accent); box-shadow: var(--accent-glow); }
.chat-message.assistant .message-avatar { background: rgba(168, 85, 247, 0.1); color: var(--secondary); border: 1px solid var(--secondary); box-shadow: var(--secondary-glow); }

.message-content { max-width: 75%; display: flex; flex-direction: column; gap: 6px; }
.chat-message.user .message-content { align-items: flex-end; }
.message-header { display: flex; align-items: center; gap: 8px; }
.chat-message.user .message-header { flex-direction: row-reverse; }
.sender-name { font-family: var(--font-heading); font-size: 12px; color: var(--foreground); letter-spacing: 1px; }
.chat-message.user .sender-name { color: var(--accent); }
.chat-message.assistant .sender-name { color: var(--secondary); }
.message-time { font-family: var(--font-accent); font-size: 11px; color: var(--text-muted); }

.message-text { padding: 12px 16px; border-radius: 8px; font-size: 14px; line-height: 1.6; font-family: var(--font-body); }
.chat-message.user .message-text { background: rgba(0, 240, 255, 0.05); color: var(--foreground); border: 1px solid var(--accent); border-bottom-right-radius: 0; box-shadow: inset 0 0 10px rgba(0, 240, 255, 0.1); }
.chat-message.assistant .message-text { background: rgba(168, 85, 247, 0.05); color: var(--foreground); border: 1px solid var(--secondary); border-bottom-left-radius: 0; box-shadow: inset 0 0 10px rgba(168, 85, 247, 0.1); }
.message-text :deep(.md-p) { margin: 0; }
.message-text :deep(.md-p:last-child) { margin-bottom: 0; }
.message-text { counter-reset: list-counter; }
.message-text :deep(.md-ol) { list-style: none; padding-left: 0; margin: 8px 0; }
.message-text :deep(.md-oli) { counter-increment: list-counter; display: flex; gap: 8px; margin: 6px 0; }
.message-text :deep(.md-oli)::before { content: counter(list-counter) "."; font-family: var(--font-accent); color: var(--accent); min-width: 20px; text-shadow: var(--accent-glow); }
.message-text :deep(.md-ul) { padding-left: 20px; list-style-type: square; color: var(--accent); margin: 8px 0; }
.message-text :deep(.md-li) { margin: 6px 0; color: var(--foreground); }
.message-text :deep(.md-li::marker) { text-shadow: var(--accent-glow); }

.typing-indicator { display: flex; gap: 6px; padding: 12px 16px; background: rgba(168, 85, 247, 0.05); border: 1px dashed var(--secondary); border-radius: 8px; border-bottom-left-radius: 0; }
.typing-indicator span { width: 6px; height: 6px; background: var(--secondary); border-radius: 0; box-shadow: var(--secondary-glow); animation: cyber-typing 1s infinite; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes cyber-typing { 0%, 100% { opacity: 0.3; transform: scale(1); } 50% { opacity: 1; transform: scale(1.5); } }

.chat-input-area { padding: 16px 24px; border-top: 1px solid var(--glass-border); background: var(--card); display: flex; gap: 12px; align-items: flex-end; }
.chat-input {
  flex: 1; padding: 12px 16px; font-size: 14px; background: rgba(0, 0, 0, 0.3); border: 1px solid var(--card-border);
  border-radius: 4px; color: var(--foreground); font-family: var(--font-body); resize: none; transition: all 0.2s ease; line-height: 1.5;
}
.chat-input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 10px rgba(0, 240, 255, 0.1) inset; }
.chat-input::placeholder { color: var(--text-muted); font-family: var(--font-accent); opacity: 0.7; }
.chat-input:disabled { background: rgba(10, 10, 15, 0.8); cursor: not-allowed; opacity: 0.5; }

.send-btn {
  width: 44px; height: 44px; background: rgba(0, 240, 255, 0.1); color: var(--accent); border: 1px solid var(--accent);
  border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease; box-shadow: var(--accent-glow);
}
.send-btn:hover:not(:disabled) { background: var(--accent); color: #000; box-shadow: 0 0 15px var(--accent); }
.send-btn:disabled { background: transparent; border-color: var(--card-border); color: var(--card-border); cursor: not-allowed; box-shadow: none; }

.survey-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: transparent; }
.survey-setup { flex: 1; display: flex; flex-direction: column; padding: 24px; border-bottom: 1px solid var(--glass-border); overflow: hidden; }
.setup-section { margin-bottom: 24px; }
.setup-section:first-child { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-height: 0; }
.setup-section:last-child { margin-bottom: 0; }

.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.setup-section .section-header .section-title { font-family: var(--font-heading); font-size: 14px; font-weight: 600; color: var(--secondary); text-transform: uppercase; letter-spacing: 1px; text-shadow: var(--secondary-glow); }
.selection-count { font-family: var(--font-accent); font-size: 12px; color: var(--accent); }

.agents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; flex: 1; overflow-y: auto; padding: 4px; align-content: start; }
.agent-checkbox {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: rgba(10, 10, 15, 0.5);
  border: 1px solid var(--card-border); border-radius: 4px; cursor: pointer; transition: all 0.2s ease;
}
.agent-checkbox:hover { border-color: var(--secondary); box-shadow: inset 0 0 10px rgba(168, 85, 247, 0.1); }
.agent-checkbox.checked { background: rgba(168, 85, 247, 0.1); border-color: var(--secondary); box-shadow: var(--secondary-glow); }
.agent-checkbox input { display: none; }

.checkbox-avatar {
  width: 28px; height: 28px; background: var(--card-border); color: var(--text-muted); border-radius: 2px;
  display: flex; align-items: center; justify-content: center; font-family: var(--font-heading); font-size: 12px; flex-shrink: 0; transition: all 0.2s ease;
}
.agent-checkbox.checked .checkbox-avatar { background: var(--secondary); color: #000; box-shadow: 0 0 10px var(--secondary); }
.checkbox-info { flex: 1; min-width: 0; }
.checkbox-name { display: block; font-family: var(--font-heading); font-size: 12px; color: var(--foreground); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.checkbox-role { display: block; font-family: var(--font-accent); font-size: 10px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.checkbox-indicator {
  width: 20px; height: 20px; border: 1px solid var(--card-border); border-radius: 2px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 0.2s ease;
}
.agent-checkbox.checked .checkbox-indicator { background: var(--secondary); border-color: var(--secondary); color: #000; box-shadow: 0 0 10px var(--secondary); }
.checkbox-indicator svg { opacity: 0; transform: scale(0.5); transition: all 0.2s ease; }
.agent-checkbox.checked .checkbox-indicator svg { opacity: 1; transform: scale(1); stroke: #000; }

.selection-actions { display: flex; gap: 8px; margin-top: 12px; }
.action-link { font-family: var(--font-accent); font-size: 12px; color: var(--secondary); background: none; border: none; cursor: pointer; padding: 0; text-transform: uppercase; }
.action-link:hover { text-shadow: var(--secondary-glow); text-decoration: underline; }
.action-divider { color: var(--card-border); }

.survey-input {
  width: 100%; padding: 14px 16px; font-size: 14px; background: rgba(0, 0, 0, 0.3); border: 1px solid var(--card-border);
  border-radius: 4px; color: var(--foreground); font-family: var(--font-body); resize: none; transition: all 0.2s ease; line-height: 1.5;
}
.survey-input:focus { outline: none; border-color: var(--secondary); box-shadow: inset 0 0 10px rgba(168, 85, 247, 0.1); }
.survey-input::placeholder { color: var(--text-muted); font-family: var(--font-accent); opacity: 0.7; }

.survey-submit-btn {
  width: 100%; padding: 14px 24px; font-family: var(--font-heading); font-size: 14px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 1px; color: var(--secondary); background: rgba(168, 85, 247, 0.1); border: 1px solid var(--secondary);
  border-radius: 4px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 20px; box-shadow: var(--secondary-glow);
}
.survey-submit-btn:hover:not(:disabled) { background: var(--secondary); color: #000; box-shadow: 0 0 20px var(--secondary); }
.survey-submit-btn:disabled { background: transparent; border-color: var(--card-border); color: var(--card-border); cursor: not-allowed; box-shadow: none; }

.loading-spinner { width: 18px; height: 18px; border: 2px solid transparent; border-top-color: currentColor; border-radius: 50%; animation: spin 0.8s linear infinite; }

.survey-results { flex: 1; overflow-y: auto; padding: 24px; }
.results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.results-title { font-family: var(--font-heading); font-size: 16px; font-weight: 700; color: var(--secondary); text-transform: uppercase; letter-spacing: 1px; text-shadow: var(--secondary-glow); }
.results-count { font-family: var(--font-accent); font-size: 12px; color: var(--accent); padding: 4px 10px; background: rgba(0, 240, 255, 0.1); border: 1px solid var(--accent); border-radius: 20px; }

.results-list { display: flex; flex-direction: column; gap: 16px; }
.result-card { background: rgba(10, 10, 15, 0.7); border: 1px solid var(--card-border); border-radius: 4px; padding: 20px; transition: all 0.2s ease; box-shadow: var(--glass-glow); }
.result-card:hover { border-color: rgba(168, 85, 247, 0.5); box-shadow: 0 0 15px rgba(168, 85, 247, 0.1); }
.result-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--card-border); }
.result-avatar { width: 40px; height: 40px; background: rgba(168, 85, 247, 0.1); color: var(--secondary); border: 1px solid var(--secondary); border-radius: 4px; display: flex; align-items: center; justify-content: center; font-family: var(--font-heading); font-size: 16px; font-weight: 700; box-shadow: var(--secondary-glow); }
.result-info { flex: 1; }
.result-name { font-family: var(--font-heading); font-size: 15px; color: var(--foreground); font-weight: 600; margin-bottom: 2px; }
.result-role { font-family: var(--font-accent); font-size: 11px; color: var(--text-muted); }
.result-question { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 16px; font-family: var(--font-body); font-size: 13px; color: var(--accent); background: rgba(0, 240, 255, 0.05); padding: 12px; border-radius: 4px; border-left: 2px solid var(--accent); }
.result-question svg { flex-shrink: 0; margin-top: 2px; color: var(--accent); filter: drop-shadow(var(--accent-glow)); }

.result-answer { font-family: var(--font-body); font-size: 14px; line-height: 1.6; color: var(--foreground); padding-left: 4px; }
.result-answer :deep(p) { margin-bottom: 12px; }
.result-answer :deep(p:last-child) { margin-bottom: 0; }
.result-answer :deep(strong) { color: var(--secondary); text-shadow: var(--secondary-glow); }

/* Podcast Styles */
.podcast-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: transparent; padding: 24px; }
.podcast-setup { flex: 1; display: flex; flex-direction: column; gap: 24px; }
.podcast-submit-btn {
  width: 100%; padding: 14px 24px; font-family: var(--font-heading); font-size: 14px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 1px; color: var(--accent); background: rgba(0, 240, 255, 0.1); border: 1px solid var(--accent);
  border-radius: 4px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: var(--accent-glow);
}
.podcast-submit-btn:hover { background: var(--accent); color: #000; box-shadow: 0 0 20px var(--accent); }
.podcast-generating-status {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; padding: 32px;
  background: rgba(10, 10, 15, 0.5); border: 1px dashed var(--accent); border-radius: 4px; border-top-left-radius: 0; box-shadow: inset 0 0 10px rgba(0, 240, 255, 0.1);
}
.podcast-player-section {
  display: flex; flex-direction: column; gap: 12px; padding: 24px; background: rgba(10, 10, 15, 0.7);
  border: 1px solid var(--accent); border-radius: 4px; box-shadow: var(--glass-glow);
}
.podcast-audio-element { width: 100%; border-radius: 4px; }
.podcast-audio-element::-webkit-media-controls-panel { background-color: rgba(255, 255, 255, 0.8); }

</style>

