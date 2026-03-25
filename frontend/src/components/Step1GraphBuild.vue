<template>
  <div class="workbench-panel">
    <div class="scroll-container">
      <!-- Step 01: Ontology -->
      <div class="step-card" :class="{ 'active': currentPhase === 0, 'completed': currentPhase > 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">온톨로지 생성</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 0" class="badge success">완료</span>
            <span v-else-if="currentPhase === 0" class="badge processing">생성 중</span>
            <span v-else class="badge pending">대기</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/graph/ontology/generate</p>
          <p class="description">
            LLM이 문서 내용과 시뮬레이션 요구사항을 분석해 핵심 현실 신호를 추출하고, 적합한 온톨로지 구조를 자동 생성합니다.
          </p>

          <!-- Loading / Progress -->
          <div v-if="currentPhase === 0 && ontologyProgress" class="progress-section">
            <div class="spinner-sm"></div>
            <span>{{ ontologyProgress.message || '문서 분석 중...' }}</span>
          </div>

          <!-- Detail Overlay -->
          <div v-if="selectedOntologyItem" class="ontology-detail-overlay">
            <div class="detail-header">
               <div class="detail-title-group">
                  <span class="detail-type-badge">{{ selectedOntologyItem.itemType === 'entity' ? 'ENTITY' : 'RELATION' }}</span>
                  <span class="detail-name">{{ selectedOntologyItem.name }}</span>
               </div>
               <button class="close-btn" @click="selectedOntologyItem = null">×</button>
            </div>
            <div class="detail-body">
               <div class="detail-desc">{{ selectedOntologyItem.description }}</div>
               
               <!-- Attributes -->
               <div class="detail-section" v-if="selectedOntologyItem.attributes?.length">
                  <span class="section-label">ATTRIBUTES</span>
                  <div class="attr-list">
                     <div v-for="attr in selectedOntologyItem.attributes" :key="attr.name" class="attr-item">
                        <span class="attr-name">{{ attr.name }}</span>
                        <span class="attr-type">({{ attr.type }})</span>
                        <span class="attr-desc">{{ attr.description }}</span>
                     </div>
                  </div>
               </div>

               <!-- Examples (Entity) -->
               <div class="detail-section" v-if="selectedOntologyItem.examples?.length">
                  <span class="section-label">EXAMPLES</span>
                  <div class="example-list">
                     <span v-for="ex in selectedOntologyItem.examples" :key="ex" class="example-tag">{{ ex }}</span>
                  </div>
               </div>

               <!-- Source/Target (Relation) -->
               <div class="detail-section" v-if="selectedOntologyItem.source_targets?.length">
                  <span class="section-label">CONNECTIONS</span>
                  <div class="conn-list">
                     <div v-for="(conn, idx) in selectedOntologyItem.source_targets" :key="idx" class="conn-item">
                        <span class="conn-node">{{ conn.source }}</span>
                        <span class="conn-arrow">→</span>
                        <span class="conn-node">{{ conn.target }}</span>
                     </div>
                  </div>
               </div>
            </div>
          </div>

          <!-- Generated Entity Tags -->
          <div v-if="projectData?.ontology?.entity_types" class="tags-container" :class="{ 'dimmed': selectedOntologyItem }">
            <span class="tag-label">GENERATED ENTITY TYPES</span>
            <div class="tags-list">
              <span 
                v-for="entity in projectData.ontology.entity_types" 
                :key="entity.name" 
                class="entity-tag clickable"
                @click="selectOntologyItem(entity, 'entity')"
              >
                {{ entity.name }}
              </span>
            </div>
          </div>

          <!-- Generated Relation Tags -->
          <div v-if="projectData?.ontology?.edge_types" class="tags-container" :class="{ 'dimmed': selectedOntologyItem }">
            <span class="tag-label">GENERATED RELATION TYPES</span>
            <div class="tags-list">
              <span 
                v-for="rel in projectData.ontology.edge_types" 
                :key="rel.name" 
                class="entity-tag clickable"
                @click="selectOntologyItem(rel, 'relation')"
              >
                {{ rel.name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: Graph Build -->
      <div class="step-card" :class="{ 'active': currentPhase === 1, 'completed': currentPhase > 1 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">GraphRAG 구축</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 1" class="badge success">완료</span>
            <span v-else-if="currentPhase === 1" class="badge processing">{{ buildProgress?.progress || 0 }}%</span>
            <span v-else class="badge pending">대기</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/graph/build</p>
          <p class="description">
            생성된 온톨로지를 기반으로 문서를 자동 분할한 뒤 Neo4j에 지식 그래프를 구축합니다. 이 과정에서 엔티티·관계를 추출합니다.
          </p>
          
          <!-- Stats Cards -->
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.nodes }}</span>
              <span class="stat-label">엔티티 노드</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.edges }}</span>
              <span class="stat-label">관계 엣지</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.types }}</span>
              <span class="stat-label">SCHEMA 유형</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 03: Complete -->
      <div class="step-card" :class="{ 'active': currentPhase === 2, 'completed': currentPhase >= 2 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">구축 완료</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase >= 2" class="badge accent">진행 중</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description">그래프 구축이 완료되었습니다. 다음 단계에서 시뮬레이션 환경을 구성해 주세요.</p>
          <button 
            class="action-btn" 
            :disabled="currentPhase < 2 || creatingSimulation"
            @click="handleEnterEnvSetup"
          >
            <span v-if="creatingSimulation" class="spinner-sm"></span>
            {{ creatingSimulation ? '생성 중...' : '환경 구성으로 이동 ➝' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SYSTEM DASHBOARD</span>
        <span class="log-id">{{ projectData?.project_id || 'NO_PROJECT' }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createSimulation } from '../api/simulation'

const router = useRouter()

const props = defineProps({
  currentPhase: { type: Number, default: 0 },
  projectData: Object,
  ontologyProgress: Object,
  buildProgress: Object,
  graphData: Object,
  systemLogs: { type: Array, default: () => [] }
})

defineEmits(['next-step'])

const selectedOntologyItem = ref(null)
const logContent = ref(null)
const creatingSimulation = ref(false)

// 환경 구성 단계로 이동: simulation 생성 후 화면 전환
const handleEnterEnvSetup = async () => {
  if (!props.projectData?.project_id || !props.projectData?.graph_id) {
    console.error('프로젝트 또는 그래프 정보가 없습니다.')
    return
  }
  
  creatingSimulation.value = true
  
  try {
    const res = await createSimulation({
      project_id: props.projectData.project_id,
      graph_id: props.projectData.graph_id,
      enable_twitter: true,
      enable_reddit: true
    })
    
    if (res.success && res.data?.simulation_id) {
      // simulation 페이지로 이동
      router.push({
        name: 'Simulation',
        params: { simulationId: res.data.simulation_id }
      })
    } else {
      console.error('시뮬레이션 생성 실패:', res.error)
      alert('시뮬레이션 생성 실패: ' + (res.error || '알 수 없는 오류'))
    }
  } catch (err) {
    console.error('시뮬레이션 생성 예외:', err)
    alert('시뮬레이션 생성 중 예외: ' + err.message)
  } finally {
    creatingSimulation.value = false
  }
}

const selectOntologyItem = (item, type) => {
  selectedOntologyItem.value = { ...item, itemType: type }
}

const graphStats = computed(() => {
  const nodes = props.graphData?.node_count || props.graphData?.nodes?.length || 0
  const edges = props.graphData?.edge_count || props.graphData?.edges?.length || 0
  const types = props.projectData?.ontology?.entity_types?.length || 0
  return { nodes, edges, types }
})

const formatDate = (dateStr) => {
  if (!dateStr) return '--:--:--'
  const d = new Date(dateStr)
  return d.toLocaleTimeString('en-US', { hour12: false }) + '.' + d.getMilliseconds()
}

// Auto-scroll logs
watch(() => props.systemLogs.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.workbench-panel {
  height: 100%;
  background-color: transparent;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  color: var(--foreground);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.step-card {
  background: var(--card);
  padding: 20px;
  border: 1px solid var(--card-border);
  transition: all 0.3s ease;
  position: relative; 
  clip-path: polygon(0 0, calc(100% - 15px) 0, 100% 15px, 100% 100%, 15px 100%, 0 calc(100% - 15px));
  box-shadow: 0 4px 15px rgba(0,0,0,0.5);
  border-left: 3px solid var(--text-muted);
}

.step-card.active {
  border-left-color: var(--accent);
  background: rgba(15, 15, 20, 0.95);
  box-shadow: var(--glass-glow), inset 0 0 20px rgba(0, 240, 255, 0.05);
  border-top-color: var(--glass-border);
  border-right-color: var(--glass-border);
  border-bottom-color: var(--glass-border);
}

.step-card.completed {
  border-left-color: var(--secondary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px dashed var(--card-border);
  padding-bottom: 12px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  font-family: var(--font-heading);
  font-size: 24px;
  font-weight: 900;
  color: var(--text-muted);
  opacity: 0.5;
}

.step-card.active .step-num {
  color: var(--accent);
  opacity: 1;
  text-shadow: var(--accent-glow);
}

.step-card.completed .step-num {
  color: var(--secondary);
  opacity: 0.8;
  text-shadow: var(--secondary-glow);
}

.step-title {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: #fff;
}

.badge {
  font-family: var(--font-accent);
  font-size: 10px;
  padding: 6px 12px;
  border-radius: 2px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  border: 1px solid transparent;
}

.badge.success { 
  background: rgba(168, 85, 247, 0.1); 
  color: var(--secondary); 
  border-color: var(--secondary);
  box-shadow: var(--secondary-glow);
}
.badge.processing { 
  background: rgba(0, 240, 255, 0.1); 
  color: var(--accent); 
  border-color: var(--accent);
  box-shadow: var(--accent-glow);
  animation: pulse-border 1.5s infinite alternate;
}
.badge.accent { 
  background: rgba(0, 240, 255, 0.1); 
  color: var(--accent); 
  border-color: var(--accent);
}
.badge.pending { 
  background: rgba(255, 255, 255, 0.05); 
  color: var(--text-muted); 
  border-color: var(--card-border);
}

@keyframes pulse-border {
  from { box-shadow: inset 0 0 5px var(--accent); }
  to { box-shadow: inset 0 0 15px var(--accent), 0 0 10px var(--accent); }
}

.api-note {
  font-family: var(--font-body);
  font-size: 11px;
  color: var(--secondary);
  margin-bottom: 12px;
  background: rgba(0,0,0,0.5);
  display: inline-block;
  padding: 4px 8px;
  border-left: 2px solid var(--secondary);
}

.description {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 20px;
}

/* Step 01 Tags */
.tags-container {
  margin-top: 20px;
  transition: opacity 0.3s;
  background: rgba(0,0,0,0.3);
  border: 1px solid var(--card-border);
  padding: 16px;
}

.tags-container.dimmed {
  opacity: 0.2;
  pointer-events: none;
}

.tag-label {
  display: block;
  font-family: var(--font-accent);
  font-size: 11px;
  color: var(--accent);
  margin-bottom: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-tag {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--card-border);
  padding: 6px 12px;
  border-radius: 2px;
  font-size: 12px;
  color: #fff;
  font-family: var(--font-body);
  transition: all 0.2s;
}

.entity-tag.clickable {
  cursor: pointer;
}

.entity-tag.clickable:hover {
  background: rgba(0, 240, 255, 0.15);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.2);
}

/* Ontology Detail Overlay */
.ontology-detail-overlay {
  position: absolute;
  top: 70px; 
  left: 20px;
  right: 20px;
  bottom: 20px;
  background: rgba(10, 10, 15, 0.95);
  backdrop-filter: blur(10px);
  z-index: 10;
  border: 1px solid var(--accent);
  box-shadow: var(--accent-glow);
  border-radius: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: crtOn 0.3s ease-out;
  clip-path: polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px));
}

@keyframes crtOn { from { opacity: 0; transform: scaleY(0.01); } to { opacity: 1; transform: scaleY(1); } }

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--accent);
  background: rgba(0, 240, 255, 0.05);
}

.detail-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-type-badge {
  font-family: var(--font-accent);
  font-size: 10px;
  font-weight: 700;
  color: #000;
  background: var(--accent);
  padding: 4px 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.detail-name {
  font-size: 16px;
  font-weight: 700;
  font-family: var(--font-heading);
  color: #fff;
  text-shadow: 0 0 5px rgba(255,255,255,0.5);
  letter-spacing: 1px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--accent);
  cursor: pointer;
  line-height: 1;
  transition: all 0.2s;
}

.close-btn:hover {
  text-shadow: var(--accent-glow);
  transform: scale(1.1);
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.detail-desc {
  font-size: 13px;
  color: var(--foreground);
  line-height: 1.6;
  font-family: var(--font-body);
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px dashed var(--card-border);
}

.detail-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-family: var(--font-accent);
  font-size: 12px;
  font-weight: 600;
  color: var(--secondary);
  margin-bottom: 12px;
  letter-spacing: 2px;
}

.attr-list, .conn-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attr-item {
  font-size: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  padding: 8px;
  background: rgba(0,0,0,0.5);
  border: 1px solid var(--card-border);
  border-left: 2px solid var(--secondary);
}

.attr-name {
  font-family: var(--font-body);
  font-weight: 600;
  color: var(--accent);
}

.attr-type {
  color: #888;
  font-size: 11px;
  font-family: var(--font-accent);
}

.attr-desc {
  color: var(--foreground);
  flex: 1;
  min-width: 150px;
}

.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-tag {
  font-size: 11px;
  font-family: var(--font-body);
  background: rgba(0,0,0,0.6);
  border: 1px solid var(--card-border);
  padding: 4px 10px;
  color: var(--text-muted);
}

.conn-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  padding: 8px;
  background: rgba(0,0,0,0.5);
  border: 1px solid var(--card-border);
  font-family: var(--font-accent);
  color: #fff;
}

.conn-node {
  font-weight: 600;
  color: var(--accent);
}

.conn-arrow {
  color: var(--secondary);
  font-weight: bold;
}

/* Step 02 Stats */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
  background: rgba(0,0,0,0.4);
  padding: 20px;
  border: 1px solid var(--glass-border);
  position: relative;
}

.stats-grid::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 4px; height: 100%;
  background: var(--accent);
  box-shadow: var(--accent-glow);
}

.stat-card {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  font-family: var(--font-heading);
  text-shadow: 0 0 10px rgba(255,255,255,0.3);
}

.stat-label {
  font-family: var(--font-accent);
  font-size: 10px;
  color: var(--accent);
  text-transform: uppercase;
  margin-top: 8px;
  letter-spacing: 1px;
  display: block;
}

/* Step 03 Button */
.action-btn {
  width: 100%;
  background: rgba(0, 240, 255, 0.1);
  color: var(--accent);
  border: 1px solid var(--accent);
  padding: 16px;
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px));
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.4), transparent);
  transition: left 0.5s ease;
}

.action-btn:hover:not(:disabled) {
  background: var(--accent);
  color: #000;
  box-shadow: var(--accent-glow);
}

.action-btn:hover:not(:disabled)::before {
  left: 100%;
}

.action-btn:disabled {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--card-border);
  color: var(--text-muted);
  cursor: not-allowed;
  box-shadow: none;
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--accent);
  font-family: var(--font-body);
  margin-bottom: 16px;
  background: rgba(0, 240, 255, 0.05);
  padding: 10px 16px;
  border-left: 2px solid var(--accent);
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: var(--accent);
  border-right-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* System Logs */
.system-logs {
  background: rgba(10, 15, 20, 0.95);
  color: var(--accent);
  padding: 16px;
  font-family: var(--font-accent);
  border: 1px solid var(--accent);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: var(--glass-glow);
}

.system-logs::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid var(--accent);
  padding-bottom: 8px;
  margin-bottom: 12px;
  font-size: 11px;
  color: var(--accent);
  font-family: var(--font-accent);
  text-transform: uppercase;
  letter-spacing: 2px;
}

.log-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-title::before {
  content: '>';
  color: var(--accent);
  animation: blink 1s step-end infinite;
}

@keyframes blink { 50% { opacity: 0; } }

.log-id {
  color: var(--text-muted);
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  height: 120px; 
  overflow-y: auto;
  padding-right: 8px;
}

.log-content::-webkit-scrollbar {
  width: 4px;
}

.log-content::-webkit-scrollbar-thumb {
  background: var(--accent);
  border-radius: 0;
}

.log-line {
  font-size: 12px;
  display: flex;
  gap: 16px;
  line-height: 1.5;
  transition: all 0.2s;
}

.log-line:hover {
  background: rgba(0, 240, 255, 0.05);
}

.log-time {
  color: var(--text-muted);
  min-width: 85px;
  font-size: 11px;
}

.log-msg {
  color: var(--foreground);
  word-break: break-all;
  text-shadow: var(--accent-glow);
}

.log-msg::before {
  content: '$ ';
  color: var(--secondary);
}
</style>
