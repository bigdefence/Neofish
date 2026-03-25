<template>
  <div class="graph-panel">
    <div class="panel-header">
      <div class="panel-title-block">
        <span class="panel-title">관계 네트워크</span>
        <span v-if="graphData" class="panel-substats">
          노드 <strong>{{ graphStats.nodes }}</strong>
          <span class="substats-sep">·</span>
          관계 <strong>{{ graphStats.edges }}</strong>
        </span>
      </div>
      <div class="header-tools">
        <button class="tool-btn" type="button" @click="$emit('refresh')" :disabled="loading" title="그래프 새로고침">
          <span class="icon-refresh" :class="{ 'spinning': loading }">↻</span>
          <span class="btn-text">새로고침</span>
        </button>
        <button class="tool-btn" type="button" @click="$emit('toggle-maximize')" title="최대화/복원">
          <span class="icon-maximize">⛶</span>
        </button>
      </div>
    </div>
    
    <div class="graph-container" ref="graphContainer">
      <!-- 그래프 시각화 -->
      <div v-if="graphData" class="graph-view">
        <div class="graph-toolbar" aria-label="그래프 도구">
          <input
            v-model="nodeSearchQuery"
            class="graph-search-input"
            type="search"
            placeholder="노드 이름 검색…"
            autocomplete="off"
            aria-label="노드 검색"
          />
        </div>
        <div class="graph-zoom-stack" aria-label="확대·축소">
          <button type="button" class="zoom-btn" title="확대" @click="zoomIn">+</button>
          <button type="button" class="zoom-btn" title="축소" @click="zoomOut">−</button>
          <button type="button" class="zoom-btn zoom-btn-fit" title="보기 초기화" @click="resetZoomView">⌖</button>
        </div>
        <svg ref="graphSvg" class="graph-svg"></svg>
        
        <!-- 구축/시뮬레이션 진행 안내 -->
        <div v-if="currentPhase === 1 || isSimulating" class="graph-building-hint">
          <div class="memory-icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="memory-icon">
              <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-4.04z" />
              <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-4.04z" />
            </svg>
          </div>
          {{ isSimulating ? 'GraphRAG 장·단기 메모리 실시간 업데이트 중' : '실시간 업데이트 중...' }}
        </div>
        
        <!-- 시뮬레이션 종료 후 안내 -->
        <div v-if="showSimulationFinishedHint" class="graph-building-hint finished-hint">
          <div class="hint-icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="hint-icon">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
          </div>
          <span class="hint-text">일부 데이터가 아직 처리 중입니다. 잠시 후 그래프를 수동 새로고침해 주세요.</span>
          <button class="hint-close-btn" @click="dismissFinishedHint" title="안내 닫기">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        <!-- 노드/엣지 상세 패널 -->
        <div v-if="selectedItem" class="detail-panel">
          <div class="detail-panel-header">
            <span class="detail-title">{{ selectedItem.type === 'node' ? '노드 정보' : '관계 정보' }}</span>
            <span v-if="selectedItem.type === 'node'" class="detail-type-badge" :style="{ background: selectedItem.color, color: '#fff' }">
              {{ selectedItem.entityType }}
            </span>
            <button class="detail-close" @click="closeDetailPanel">×</button>
          </div>
          
          <!-- 노드 상세 -->
          <div v-if="selectedItem.type === 'node'" class="detail-content">
            <div class="detail-row">
              <span class="detail-label">이름</span>
              <span class="detail-value">{{ selectedItem.data.name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">UUID</span>
              <span class="detail-value uuid-text">{{ selectedItem.data.uuid }}</span>
            </div>
            <div class="detail-row" v-if="selectedItem.data.created_at">
              <span class="detail-label">생성</span>
              <span class="detail-value">{{ formatDateTime(selectedItem.data.created_at) }}</span>
            </div>
            
            <!-- Properties -->
            <div class="detail-section" v-if="selectedItem.data.attributes && Object.keys(selectedItem.data.attributes).length > 0">
              <div class="section-title">속성</div>
              <div class="properties-list">
                <div v-for="(value, key) in selectedItem.data.attributes" :key="key" class="property-item">
                  <span class="property-key">{{ key }}:</span>
                  <span class="property-value">{{ value || 'None' }}</span>
                </div>
              </div>
            </div>
            
            <!-- Summary -->
            <div class="detail-section" v-if="selectedItem.data.summary">
              <div class="section-title">요약</div>
              <div class="summary-text">{{ selectedItem.data.summary }}</div>
            </div>
            
            <!-- Labels -->
            <div class="detail-section" v-if="selectedItem.data.labels && selectedItem.data.labels.length > 0">
              <div class="section-title">라벨</div>
              <div class="labels-list">
                <span v-for="label in selectedItem.data.labels" :key="label" class="label-tag">
                  {{ label }}
                </span>
              </div>
            </div>
          </div>
          
          <!-- 엣지 상세 -->
          <div v-else class="detail-content">
            <!-- 자기 루프 그룹 상세 -->
            <template v-if="selectedItem.data.isSelfLoopGroup">
              <div class="edge-relation-header self-loop-header">
                {{ selectedItem.data.source_name }} — 자기 관계
                <span class="self-loop-count">{{ selectedItem.data.selfLoopCount }}건</span>
              </div>
              
              <div class="self-loop-list">
                <div 
                  v-for="(loop, idx) in selectedItem.data.selfLoopEdges" 
                  :key="loop.uuid || idx" 
                  class="self-loop-item"
                  :class="{ expanded: expandedSelfLoops.has(loop.uuid || idx) }"
                >
                  <div 
                    class="self-loop-item-header"
                    @click="toggleSelfLoop(loop.uuid || idx)"
                  >
                    <span class="self-loop-index">#{{ idx + 1 }}</span>
                    <span class="self-loop-name">{{ loop.name || loop.fact_type || 'RELATED' }}</span>
                    <span class="self-loop-toggle">{{ expandedSelfLoops.has(loop.uuid || idx) ? '−' : '+' }}</span>
                  </div>
                  
                  <div class="self-loop-item-content" v-show="expandedSelfLoops.has(loop.uuid || idx)">
                    <div class="detail-row" v-if="loop.uuid">
                      <span class="detail-label">UUID</span>
                      <span class="detail-value uuid-text">{{ loop.uuid }}</span>
                    </div>
                    <div class="detail-row" v-if="loop.fact">
                      <span class="detail-label">사실</span>
                      <span class="detail-value fact-text">{{ loop.fact }}</span>
                    </div>
                    <div class="detail-row" v-if="loop.fact_type">
                      <span class="detail-label">유형</span>
                      <span class="detail-value">{{ loop.fact_type }}</span>
                    </div>
                    <div class="detail-row" v-if="loop.created_at">
                      <span class="detail-label">생성</span>
                      <span class="detail-value">{{ formatDateTime(loop.created_at) }}</span>
                    </div>
                    <div v-if="loop.episodes && loop.episodes.length > 0" class="self-loop-episodes">
                      <span class="detail-label">에피소드</span>
                      <div class="episodes-list compact">
                        <span v-for="ep in loop.episodes" :key="ep" class="episode-tag small">{{ ep }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            
            <!-- 일반 엣지 상세 -->
            <template v-else>
              <div class="edge-relation-header">
                {{ selectedItem.data.source_name }} → {{ selectedItem.data.name || 'RELATED_TO' }} → {{ selectedItem.data.target_name }}
              </div>
              
              <div class="detail-row">
                <span class="detail-label">UUID</span>
                <span class="detail-value uuid-text">{{ selectedItem.data.uuid }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">라벨</span>
                <span class="detail-value">{{ selectedItem.data.name || 'RELATED_TO' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">유형</span>
                <span class="detail-value">{{ selectedItem.data.fact_type || 'Unknown' }}</span>
              </div>
              <div class="detail-row" v-if="selectedItem.data.fact">
                <span class="detail-label">사실</span>
                <span class="detail-value fact-text">{{ selectedItem.data.fact }}</span>
              </div>
              
              <!-- Episodes -->
              <div class="detail-section" v-if="selectedItem.data.episodes && selectedItem.data.episodes.length > 0">
                <div class="section-title">에피소드</div>
                <div class="episodes-list">
                  <span v-for="ep in selectedItem.data.episodes" :key="ep" class="episode-tag">
                    {{ ep }}
                  </span>
                </div>
              </div>
              
              <div class="detail-row" v-if="selectedItem.data.created_at">
                <span class="detail-label">생성</span>
                <span class="detail-value">{{ formatDateTime(selectedItem.data.created_at) }}</span>
              </div>
              <div class="detail-row" v-if="selectedItem.data.valid_at">
                <span class="detail-label">유효 시작</span>
                <span class="detail-value">{{ formatDateTime(selectedItem.data.valid_at) }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
      
      <!-- 로딩 상태 -->
      <div v-else-if="loading" class="graph-state">
        <div class="loading-spinner"></div>
        <p>그래프 데이터 로딩 중...</p>
      </div>
      
      <!-- 대기/빈 상태 -->
      <div v-else class="graph-state">
        <div class="empty-icon">❖</div>
        <p class="empty-text">온톨로지 생성을 기다리는 중...</p>
      </div>
    </div>

    <!-- 하단 범례 (좌측 하단) -->
    <div v-if="graphData && entityTypes.length" class="graph-legend">
      <span class="legend-title">엔터티 유형</span>
      <div class="legend-items">
        <div class="legend-item" v-for="type in entityTypes" :key="type.name">
          <span class="legend-dot" :style="{ background: type.color }"></span>
          <span class="legend-label">{{ type.name }} <span class="legend-count">({{ type.count }})</span></span>
        </div>
      </div>
    </div>
    
    <!-- 엣지 라벨 표시 스위치 -->
    <div v-if="graphData" class="edge-labels-toggle">
      <label class="toggle-switch">
        <input type="checkbox" v-model="showEdgeLabels" />
        <span class="slider"></span>
      </label>
      <span class="toggle-label">관계 라벨</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  graphData: Object,
  loading: Boolean,
  currentPhase: Number,
  isSimulating: Boolean
})

const emit = defineEmits(['refresh', 'toggle-maximize'])

const graphContainer = ref(null)
const graphSvg = ref(null)
const selectedItem = ref(null)
const showEdgeLabels = ref(true)
const graphRenderTimer = ref(null)
const nodeSearchQuery = ref('')
let searchDebounceTimer = null

/** d3-zoom 인스턴스·svg 선택 (툴바 버튼용) */
let currentZoomBehavior = null
let currentSvgSelection = null

const graphStats = computed(() => {
  const gd = props.graphData
  if (!gd) return { nodes: 0, edges: 0 }
  return {
    nodes: (gd.nodes || []).length,
    edges: (gd.edges || []).length
  }
})

const edgeTypePalette = [
  '#38bdf8', '#a78bfa', '#f472b6', '#34d399', '#fbbf24',
  '#22d3ee', '#818cf8', '#fb923c', '#2dd4bf', '#e879f9'
]

function edgeAccentColor (edge) {
  const key = String(edge?.type || edge?.name || 'RELATED')
  let h = 2166136261
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return edgeTypePalette[Math.abs(h) % edgeTypePalette.length]
}

function edgeStrokeWidth (d) {
  const n = d.pairTotal || 1
  return Math.min(2.8, 1.2 + (n - 1) * 0.35)
}

function truncateEdgeLabel (name, max = 20) {
  const s = String(name || '')
  return s.length > max ? `${s.slice(0, max)}…` : s
} 
const expandedSelfLoops = ref(new Set()) 
const showSimulationFinishedHint = ref(false) 
const wasSimulating = ref(false) 

const createGraphSignature = (graphData) => {
  if (!graphData) return 'empty'

  const nodes = graphData.nodes || []
  const edges = graphData.edges || []
  let hash = 2166136261

  const add = (value) => {
    const str = String(value || '')
    for (let i = 0; i < str.length; i++) {
      hash ^= str.charCodeAt(i)
      hash = Math.imul(hash, 16777619)
    }
  }

  add(graphData.graph_id)
  add(nodes.length)
  add(edges.length)

  nodes.forEach((node) => {
    add(node.uuid)
    add(node.name)
    ;(node.labels || []).forEach(add)
  })

  edges.forEach((edge) => {
    add(edge.source_node_uuid)
    add(edge.target_node_uuid)
    add(edge.fact_type || edge.name)
  })

  return `${nodes.length}:${edges.length}:${hash >>> 0}`
}

const graphRenderSignature = computed(() => createGraphSignature(props.graphData))

const scheduleRender = () => {
  if (graphRenderTimer.value) {
    clearTimeout(graphRenderTimer.value)
  }

  graphRenderTimer.value = setTimeout(() => {
    graphRenderTimer.value = null
    nextTick(renderGraph)
  }, 60)
}


const dismissFinishedHint = () => {
  showSimulationFinishedHint.value = false
}


watch(() => props.isSimulating, (newValue, oldValue) => {
  if (wasSimulating.value && !newValue) {
    
    showSimulationFinishedHint.value = true
  }
  wasSimulating.value = newValue
}, { immediate: true })


const toggleSelfLoop = (id) => {
  const newSet = new Set(expandedSelfLoops.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  expandedSelfLoops.value = newSet
}


const entityTypes = computed(() => {
  if (!props.graphData?.nodes) return []
  const typeMap = {}
  
  const colors = [
    '#f97316', '#38bdf8', '#a78bfa', '#34d399', '#fb7185',
    '#fbbf24', '#22d3ee', '#c084fc', '#4ade80', '#818cf8'
  ]
  
  props.graphData.nodes.forEach(node => {
    const type = node.labels?.find(l => l !== 'Entity') || 'Entity'
    if (!typeMap[type]) {
      typeMap[type] = { name: type, count: 0, color: colors[Object.keys(typeMap).length % colors.length] }
    }
    typeMap[type].count++
  })
  return Object.values(typeMap)
})


const formatDateTime = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

function resetZoomView () {
  if (currentSvgSelection && currentZoomBehavior) {
    currentSvgSelection
      .transition()
      .duration(280)
      .call(currentZoomBehavior.transform, d3.zoomIdentity)
  }
}

function zoomIn () {
  if (currentSvgSelection && currentZoomBehavior) {
    currentSvgSelection
      .transition()
      .duration(200)
      .call(currentZoomBehavior.scaleBy, 1.28)
  }
}

function zoomOut () {
  if (currentSvgSelection && currentZoomBehavior) {
    currentSvgSelection
      .transition()
      .duration(200)
      .call(currentZoomBehavior.scaleBy, 1 / 1.28)
  }
}

const closeDetailPanel = () => {
  selectedItem.value = null
  expandedSelfLoops.value = new Set() 
}

let currentSimulation = null
let linkLabelsRef = null
let linkLabelBgRef = null

const renderGraph = () => {
  if (!graphSvg.value || !props.graphData) return
  
  
  if (currentSimulation) {
    currentSimulation.stop()
  }
  
  const container = graphContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  const svgEl = graphSvg.value
  let prevTransform = d3.zoomIdentity
  if (svgEl) {
    try {
      prevTransform = d3.zoomTransform(svgEl)
    } catch {
      prevTransform = d3.zoomIdentity
    }
  }
  
  const svg = d3.select(graphSvg.value)
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    
  svg.selectAll('*').remove()

  const gradId = (name) => `ng-${String(name).replace(/[^a-zA-Z0-9_-]/g, '_')}`

  const defs = svg.append('defs')

  const linkGlow = defs.append('filter')
    .attr('id', 'mx-link-glow')
    .attr('x', '-40%')
    .attr('y', '-40%')
    .attr('width', '180%')
    .attr('height', '180%')
  linkGlow.append('feGaussianBlur')
    .attr('stdDeviation', 1.4)
    .attr('result', 'blur')
  const lgMerge = linkGlow.append('feMerge')
  lgMerge.append('feMergeNode').attr('in', 'blur')
  lgMerge.append('feMergeNode').attr('in', 'SourceGraphic')

  const nodeGlow = defs.append('filter')
    .attr('id', 'mx-node-glow')
    .attr('x', '-60%')
    .attr('y', '-60%')
    .attr('width', '220%')
    .attr('height', '220%')
  nodeGlow.append('feGaussianBlur')
    .attr('stdDeviation', 2.2)
    .attr('result', 'nb')
  const ngMerge = nodeGlow.append('feMerge')
  ngMerge.append('feMergeNode').attr('in', 'nb')
  ngMerge.append('feMergeNode').attr('in', 'SourceGraphic')

  entityTypes.value.forEach((t) => {
    const gid = gradId(t.name)
    const c = d3.color(t.color)
    const g = defs.append('linearGradient')
      .attr('id', gid)
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '100%')
      .attr('y2', '100%')
    if (c) {
      g.append('stop').attr('offset', '0%').attr('stop-color', c.brighter(0.85))
      g.append('stop').attr('offset', '55%').attr('stop-color', t.color)
      g.append('stop').attr('offset', '100%').attr('stop-color', c.darker(0.6))
    } else {
      g.append('stop').attr('offset', '0%').attr('stop-color', t.color)
      g.append('stop').attr('offset', '100%').attr('stop-color', t.color)
    }
  })

  const nodesData = props.graphData.nodes || []
  const edgesData = props.graphData.edges || []
  
  if (nodesData.length === 0) return

  // Prep data
  const nodeMap = {}
  nodesData.forEach(n => nodeMap[n.uuid] = n)
  
  const nodes = nodesData.map(n => ({
    id: n.uuid,
    name: n.name || 'Unnamed',
    type: n.labels?.find(l => l !== 'Entity') || 'Entity',
    rawData: n
  }))
  
  const nodeIds = new Set(nodes.map(n => n.id))
  
  
  const edgePairCount = {}
  const selfLoopEdges = {} 
  const tempEdges = edgesData
    .filter(e => nodeIds.has(e.source_node_uuid) && nodeIds.has(e.target_node_uuid))
  
  
  tempEdges.forEach(e => {
    if (e.source_node_uuid === e.target_node_uuid) {
      
      if (!selfLoopEdges[e.source_node_uuid]) {
        selfLoopEdges[e.source_node_uuid] = []
      }
      selfLoopEdges[e.source_node_uuid].push({
        ...e,
        source_name: nodeMap[e.source_node_uuid]?.name,
        target_name: nodeMap[e.target_node_uuid]?.name
      })
    } else {
      const pairKey = [e.source_node_uuid, e.target_node_uuid].sort().join('_')
      edgePairCount[pairKey] = (edgePairCount[pairKey] || 0) + 1
    }
  })
  
  
  const edgePairIndex = {}
  const processedSelfLoopNodes = new Set() 
  
  const edges = []
  
  tempEdges.forEach(e => {
    const isSelfLoop = e.source_node_uuid === e.target_node_uuid
    
    if (isSelfLoop) {
      
      if (processedSelfLoopNodes.has(e.source_node_uuid)) {
        return 
      }
      processedSelfLoopNodes.add(e.source_node_uuid)
      
      const allSelfLoops = selfLoopEdges[e.source_node_uuid]
      const nodeName = nodeMap[e.source_node_uuid]?.name || 'Unknown'
      
      edges.push({
        source: e.source_node_uuid,
        target: e.target_node_uuid,
        type: 'SELF_LOOP',
        name: `Self Relations (${allSelfLoops.length})`,
        curvature: 0,
        isSelfLoop: true,
        rawData: {
          isSelfLoopGroup: true,
          source_name: nodeName,
          target_name: nodeName,
          selfLoopCount: allSelfLoops.length,
          selfLoopEdges: allSelfLoops 
        }
      })
      return
    }
    
    const pairKey = [e.source_node_uuid, e.target_node_uuid].sort().join('_')
    const totalCount = edgePairCount[pairKey]
    const currentIndex = edgePairIndex[pairKey] || 0
    edgePairIndex[pairKey] = currentIndex + 1
    
    
    const isReversed = e.source_node_uuid > e.target_node_uuid
    
    
    let curvature = 0
    if (totalCount > 1) {
      
      
      const curvatureRange = Math.min(1.2, 0.6 + totalCount * 0.15)
      curvature = ((currentIndex / (totalCount - 1)) - 0.5) * curvatureRange * 2
      
      
      
      if (isReversed) {
        curvature = -curvature
      }
    }
    
    edges.push({
      source: e.source_node_uuid,
      target: e.target_node_uuid,
      type: e.fact_type || e.name || 'RELATED',
      name: e.name || e.fact_type || 'RELATED',
      curvature,
      isSelfLoop: false,
      pairIndex: currentIndex,
      pairTotal: totalCount,
      rawData: {
        ...e,
        source_name: nodeMap[e.source_node_uuid]?.name,
        target_name: nodeMap[e.target_node_uuid]?.name
      }
    })
  })

  const adjacency = new Map(nodes.map((n) => [n.id, new Set()]))
  edges.forEach((e) => {
    const s = e.source
    const t = e.target
    adjacency.get(s)?.add(t)
    adjacency.get(t)?.add(s)
  })

  let hoverId = null
  let hoverLeaveTimer = null

  // Color scale
  const colorMap = {}
  entityTypes.value.forEach(t => colorMap[t.name] = t.color)
  const getColor = (type) => colorMap[type] || '#94a3b8'
  const nodeFill = (type) => (colorMap[type] ? `url(#${gradId(type)})` : getColor(type))

  
  const nCount = nodes.length
  const chargeStrength = nCount > 80 ? -720 : nCount > 40 ? -600 : -520
  const collideR = nCount > 80 ? 48 : 56

  const simulation = d3.forceSimulation(nodes)
    .alphaDecay(0.022)
    .velocityDecay(0.38)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(d => {
      const baseDistance = 150
      const edgeCount = d.pairTotal || 1
      return baseDistance + (edgeCount - 1) * 50
    }))
    .force('charge', d3.forceManyBody().strength(chargeStrength))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide(collideR))
    .force('x', d3.forceX(width / 2).strength(0.055))
    .force('y', d3.forceY(height / 2).strength(0.055))
  
  currentSimulation = simulation

  const g = svg.append('g')
  
  const zoom = d3.zoom()
    .extent([[0, 0], [width, height]])
    .scaleExtent([0.12, 6])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  svg.call(zoom)
  currentZoomBehavior = zoom
  currentSvgSelection = svg

  if (prevTransform.k !== 1 || Math.abs(prevTransform.x) > 0.01 || Math.abs(prevTransform.y) > 0.01) {
    svg.call(zoom.transform, prevTransform)
  }

  
  const linkGroup = g.append('g').attr('class', 'links')
  
  
  const getLinkPath = (d) => {
    const sx = d.source.x, sy = d.source.y
    const tx = d.target.x, ty = d.target.y
    
    
    if (d.isSelfLoop) {
      
      const loopRadius = 30
      
      const x1 = sx + 8  
      const y1 = sy - 4
      const x2 = sx + 8  
      const y2 = sy + 4
      
      return `M${x1},${y1} A${loopRadius},${loopRadius} 0 1,1 ${x2},${y2}`
    }
    
    if (d.curvature === 0) {
      
      return `M${sx},${sy} L${tx},${ty}`
    }
    
    
    const dx = tx - sx, dy = ty - sy
    const dist = Math.sqrt(dx * dx + dy * dy)
    
    
    const pairTotal = d.pairTotal || 1
    const offsetRatio = 0.25 + pairTotal * 0.05 
    const baseOffset = Math.max(35, dist * offsetRatio)
    const offsetX = -dy / dist * d.curvature * baseOffset
    const offsetY = dx / dist * d.curvature * baseOffset
    const cx = (sx + tx) / 2 + offsetX
    const cy = (sy + ty) / 2 + offsetY
    
    return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`
  }
  
  
  const getLinkMidpoint = (d) => {
    const sx = d.source.x, sy = d.source.y
    const tx = d.target.x, ty = d.target.y
    
    
    if (d.isSelfLoop) {
      
      return { x: sx + 70, y: sy }
    }
    
    if (d.curvature === 0) {
      return { x: (sx + tx) / 2, y: (sy + ty) / 2 }
    }
    
    
    const dx = tx - sx, dy = ty - sy
    const dist = Math.sqrt(dx * dx + dy * dy)
    const pairTotal = d.pairTotal || 1
    const offsetRatio = 0.25 + pairTotal * 0.05
    const baseOffset = Math.max(35, dist * offsetRatio)
    const offsetX = -dy / dist * d.curvature * baseOffset
    const offsetY = dx / dist * d.curvature * baseOffset
    const cx = (sx + tx) / 2 + offsetX
    const cy = (sy + ty) / 2 + offsetY
    
    
    const midX = 0.25 * sx + 0.5 * cx + 0.25 * tx
    const midY = 0.25 * sy + 0.5 * cy + 0.25 * ty
    
    return { x: midX, y: midY }
  }
  
  const resetLinkVisuals = () => {
    linkGroup.selectAll('path.edge-path').each(function (d) {
      d3.select(this)
        .attr('stroke', edgeAccentColor(d))
        .attr('stroke-width', edgeStrokeWidth(d))
        .attr('stroke-opacity', 0.5)
    })
    linkGroup.selectAll('rect.edge-label-bg')
      .attr('fill', 'rgba(15, 23, 42, 0.88)')
      .attr('stroke', 'rgba(99, 102, 241, 0.35)')
    linkGroup.selectAll('text.edge-label-text')
      .attr('fill', '#e2e8f0')
  }

  const link = linkGroup.selectAll('path')
    .data(edges)
    .enter().append('path')
    .attr('class', 'edge-path')
    .attr('stroke', d => edgeAccentColor(d))
    .attr('stroke-width', d => edgeStrokeWidth(d))
    .attr('stroke-opacity', 0.5)
    .attr('stroke-linecap', 'round')
    .attr('fill', 'none')
    .attr('filter', 'url(#mx-link-glow)')
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      resetLinkVisuals()
      linkLabelBg.filter(l => l === d).attr('fill', 'rgba(30, 41, 59, 0.95)').attr('stroke', 'rgba(56, 189, 248, 0.65)')
      linkLabels.filter(l => l === d).attr('fill', '#f8fafc')
      d3.select(event.target)
        .attr('stroke', edgeAccentColor(d))
        .attr('stroke-width', Math.max(3, edgeStrokeWidth(d) + 1.2))
        .attr('stroke-opacity', 1)
      selectedItem.value = {
        type: 'edge',
        data: d.rawData
      }
    })

  
  const linkLabelBg = linkGroup.selectAll('rect')
    .data(edges)
    .enter().append('rect')
    .attr('class', 'edge-label-bg')
    .attr('fill', 'rgba(15, 23, 42, 0.88)')
    .attr('stroke', 'rgba(99, 102, 241, 0.35)')
    .attr('stroke-width', 1)
    .attr('rx', 8)
    .attr('ry', 8)
    .style('cursor', 'pointer')
    .style('pointer-events', 'all')
    .style('display', showEdgeLabels.value ? 'block' : 'none')
    .on('click', (event, d) => {
      event.stopPropagation()
      resetLinkVisuals()
      link.filter(l => l === d)
        .attr('stroke', edgeAccentColor(d))
        .attr('stroke-width', Math.max(3, edgeStrokeWidth(d) + 1.2))
        .attr('stroke-opacity', 1)
      d3.select(event.target).attr('fill', 'rgba(30, 58, 138, 0.55)').attr('stroke', 'rgba(56, 189, 248, 0.65)')
      linkLabels.filter(l => l === d).attr('fill', '#f8fafc')
      selectedItem.value = {
        type: 'edge',
        data: d.rawData
      }
    })

  // Link labels
  const linkLabels = linkGroup.selectAll('text')
    .data(edges)
    .enter().append('text')
    .attr('class', 'edge-label-text')
    .each(function (d) {
      d3.select(this).append('title').text(d.name)
    })
    .text(d => truncateEdgeLabel(d.name, 22))
    .attr('font-size', '8.5px')
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.04em')
    .attr('fill', '#e2e8f0')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'middle')
    .style('cursor', 'pointer')
    .style('pointer-events', 'all')
    .style('font-family', 'ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif')
    .style('display', showEdgeLabels.value ? 'block' : 'none')
    .on('click', (event, d) => {
      event.stopPropagation()
      resetLinkVisuals()
      link.filter(l => l === d)
        .attr('stroke', edgeAccentColor(d))
        .attr('stroke-width', Math.max(3, edgeStrokeWidth(d) + 1.2))
        .attr('stroke-opacity', 1)
      linkLabelBg.filter(l => l === d).attr('fill', 'rgba(30, 41, 59, 0.95)').attr('stroke', 'rgba(56, 189, 248, 0.65)')
      d3.select(event.target).attr('fill', '#f8fafc')
      selectedItem.value = {
        type: 'edge',
        data: d.rawData
      }
    })

  linkLabels.each(function (d) {
    const bbox = this.getBBox()
    d._labelWidth = bbox.width
    d._labelHeight = bbox.height
  })

  
  linkLabelsRef = linkLabels
  linkLabelBgRef = linkLabelBg

  const applyFocusOpacity = () => {
    const q = nodeSearchQuery.value.trim().toLowerCase()
    const nodeMatchById = (id) => {
      if (!q) return true
      return ((nodeMap[id]?.name) || '').toLowerCase().includes(q)
    }

    const neighborSet = hoverId
      ? new Set([hoverId, ...(adjacency.get(hoverId) || [])])
      : null

    node.style('opacity', (d) => {
      if (neighborSet) {
        if (!neighborSet.has(d.id)) return 0.14
      }
      if (!q) return 1
      return (d.name || '').toLowerCase().includes(q) ? 1 : 0.2
    })

    const linkOp = (d) => {
      const sid = typeof d.source === 'object' ? d.source.id : d.source
      const tid = typeof d.target === 'object' ? d.target.id : d.target
      if (neighborSet) {
        if (sid === hoverId || tid === hoverId) return 0.92
        return 0.06
      }
      if (!q) return 1
      return nodeMatchById(sid) || nodeMatchById(tid) ? 0.88 : 0.08
    }

    link.style('opacity', linkOp)
    linkLabels.style('opacity', linkOp)
    linkLabelBg.style('opacity', linkOp)
  }

  // Nodes group (halo + core + label in one <g>)
  const nodeGroup = g.append('g').attr('class', 'nodes')

  const nodeDrag = d3.drag()
    .on('start', (event, d) => {
      d.fx = d.x
      d.fy = d.y
      d._dragStartX = event.x
      d._dragStartY = event.y
      d._isDragging = false
    })
    .on('drag', (event, d) => {
      const dx = event.x - d._dragStartX
      const dy = event.y - d._dragStartY
      const distance = Math.sqrt(dx * dx + dy * dy)
      if (!d._isDragging && distance > 3) {
        d._isDragging = true
        simulation.alphaTarget(0.3).restart()
      }
      if (d._isDragging) {
        d.fx = event.x
        d.fy = event.y
      }
    })
    .on('end', (event, d) => {
      if (d._isDragging) {
        simulation.alphaTarget(0)
      }
      d.fx = null
      d.fy = null
      d._isDragging = false
    })

  const setNodeIdleStroke = (gSel) => {
    gSel.select('circle.core')
      .attr('stroke', 'rgba(248, 250, 252, 0.92)')
      .attr('stroke-width', 2.2)
  }

  const node = nodeGroup.selectAll('g.graph-node')
    .data(nodes)
    .enter().append('g')
    .attr('class', 'graph-node')
    .style('cursor', 'pointer')
    .call(nodeDrag)
    .on('click', (event, d) => {
      event.stopPropagation()
      node.each(function () {
        setNodeIdleStroke(d3.select(this))
      })
      resetLinkVisuals()
      const gEl = d3.select(event.currentTarget)
      gEl.select('circle.core')
        .attr('stroke', '#38bdf8')
        .attr('stroke-width', 3.2)
      link.filter(l => l.source.id === d.id || l.target.id === d.id)
        .attr('stroke', l => edgeAccentColor(l))
        .attr('stroke-width', l => Math.max(2.6, edgeStrokeWidth(l) + 0.8))
        .attr('stroke-opacity', 0.95)
      selectedItem.value = {
        type: 'node',
        data: d.rawData,
        entityType: d.type,
        color: getColor(d.type)
      }
    })
    .on('mouseenter', (event, d) => {
      if (hoverLeaveTimer) {
        clearTimeout(hoverLeaveTimer)
        hoverLeaveTimer = null
      }
      hoverId = d.id
      applyFocusOpacity()
      if (!selectedItem.value || selectedItem.value.data?.uuid !== d.rawData.uuid) {
        d3.select(event.currentTarget).select('circle.halo').attr('opacity', 0.35)
        d3.select(event.currentTarget).select('circle.core')
          .attr('stroke', 'rgba(56, 189, 248, 0.9)')
          .attr('stroke-width', 2.6)
      }
    })
    .on('mouseleave', (event, d) => {
      hoverLeaveTimer = setTimeout(() => {
        hoverId = null
        applyFocusOpacity()
        hoverLeaveTimer = null
      }, 42)
      if (!selectedItem.value || selectedItem.value.data?.uuid !== d.rawData.uuid) {
        d3.select(event.currentTarget).select('circle.halo').attr('opacity', 0.18)
        setNodeIdleStroke(d3.select(event.currentTarget))
      }
    })

  node.append('circle')
    .attr('class', 'halo')
    .attr('r', 22)
    .attr('fill', d => getColor(d.type))
    .attr('opacity', 0.18)

  node.append('circle')
    .attr('class', 'core')
    .attr('r', 11)
    .attr('fill', d => nodeFill(d.type))
    .attr('stroke', 'rgba(248, 250, 252, 0.92)')
    .attr('stroke-width', 2.2)
    .attr('filter', 'url(#mx-node-glow)')

  node.append('text')
    .attr('class', 'graph-node-label')
    .text(d => (d.name.length > 14 ? d.name.substring(0, 14) + '…' : d.name))
    .attr('font-size', '11.5px')
    .attr('font-weight', '600')
    .attr('fill', '#f1f5f9')
    .attr('dx', 16)
    .attr('dy', 4)
    .style('pointer-events', 'none')
    .style('font-family', 'ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif')
    .style('paint-order', 'stroke fill')
    .attr('stroke', 'rgba(15, 23, 42, 0.88)')
    .attr('stroke-width', 3)
    .attr('stroke-linejoin', 'round')

  simulation.on('tick', () => {
    
    link.attr('d', d => getLinkPath(d))

    if (showEdgeLabels.value) {
      linkLabels.each(function(d) {
        const mid = getLinkMidpoint(d)
        d3.select(this)
          .attr('x', mid.x)
          .attr('y', mid.y)
          .attr('transform', '') 
      })

      linkLabelBg.each(function(d) {
        const mid = getLinkMidpoint(d)
        const width = d._labelWidth || 0
        const height = d._labelHeight || 0
        d3.select(this)
          .attr('x', mid.x - width / 2 - 4)
          .attr('y', mid.y - height / 2 - 2)
          .attr('width', width + 8)
          .attr('height', height + 4)
          .attr('transform', '') 
      })
    }

    node.attr('transform', d => `translate(${d.x},${d.y})`)
  })
  
  
  svg.on('click', () => {
    hoverId = null
    if (hoverLeaveTimer) {
      clearTimeout(hoverLeaveTimer)
      hoverLeaveTimer = null
    }
    applyFocusOpacity()
    selectedItem.value = null
    node.each(function () {
      setNodeIdleStroke(d3.select(this))
      d3.select(this).select('circle.halo').attr('opacity', 0.18)
    })
    resetLinkVisuals()
  })

  applyFocusOpacity()
}

watch(graphRenderSignature, () => {
  scheduleRender()
}, { immediate: true })

watch(nodeSearchQuery, () => {
  clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => scheduleRender(), 180)
})

watch(showEdgeLabels, (newVal) => {
  if (linkLabelsRef) {
    linkLabelsRef.style('display', newVal ? 'block' : 'none')
  }
  if (linkLabelBgRef) {
    linkLabelBgRef.style('display', newVal ? 'block' : 'none')
  }
})

const handleResize = () => {
  scheduleRender()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  if (props.graphData) {
    scheduleRender()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (graphRenderTimer.value) {
    clearTimeout(graphRenderTimer.value)
  }
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  if (currentSimulation) {
    currentSimulation.stop()
  }
})
</script>

<style scoped>
.graph-panel {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: #0a0c14;
  background-image:
    radial-gradient(ellipse 120% 80% at 50% -20%, rgba(56, 189, 248, 0.14), transparent 55%),
    radial-gradient(ellipse 90% 70% at 100% 60%, rgba(139, 92, 246, 0.1), transparent 50%),
    radial-gradient(ellipse 70% 50% at 0% 80%, rgba(244, 114, 182, 0.08), transparent 45%),
    radial-gradient(rgba(148, 163, 184, 0.11) 1px, transparent 1px);
  background-size: auto, auto, auto, 28px 28px;
  animation: graph-panel-bg-drift 28s ease-in-out infinite alternate;
}

@media (prefers-reduced-motion: reduce) {
  .graph-panel {
    animation: none;
  }
}

@keyframes graph-panel-bg-drift {
  0% { background-position: 0% 0%, 0% 0%, 0% 0%, 0 0; }
  100% { background-position: 0% 0%, 0% 0%, 0% 0%, 14px 14px; }
}

.panel-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 14px 20px;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  background: linear-gradient(to bottom, rgba(10, 12, 20, 0.94), rgba(10, 12, 20, 0));
  pointer-events: none;
  border-bottom: 1px solid transparent;
}

.panel-title-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  pointer-events: auto;
  min-width: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #e2e8f0;
  text-shadow: 0 0 24px rgba(56, 189, 248, 0.35);
}

.panel-substats {
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.02em;
}

.panel-substats strong {
  color: #cbd5e1;
  font-weight: 600;
}

.substats-sep {
  opacity: 0.45;
  margin: 0 2px;
}

.header-tools {
  pointer-events: auto;
  display: flex;
  gap: 10px;
  align-items: center;
}

.tool-btn {
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(99, 102, 241, 0.35);
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  color: #cbd5e1;
  transition: border-color 0.2s, box-shadow 0.2s, color 0.2s;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.2), 0 4px 20px rgba(0, 0, 0, 0.25);
  font-size: 13px;
}

.tool-btn:hover {
  color: #f8fafc;
  border-color: rgba(56, 189, 248, 0.55);
  box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
}

.tool-btn .btn-text {
  font-size: 12px;
}

.icon-refresh.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.graph-toolbar {
  position: absolute;
  top: 52px;
  left: 20px;
  z-index: 11;
  max-width: min(360px, calc(100% - 220px));
  pointer-events: none;
}

.graph-search-input {
  pointer-events: auto;
  width: 100%;
  height: 36px;
  padding: 0 14px 0 38px;
  border-radius: 10px;
  border: 1px solid rgba(99, 102, 241, 0.35);
  background: rgba(15, 23, 42, 0.88) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Ccircle cx='7' cy='7' r='5'/%3E%3Cpath d='M11 11l3 3'/%3E%3C/svg%3E") 12px center no-repeat;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.graph-search-input::placeholder {
  color: #64748b;
}

.graph-search-input:focus {
  border-color: rgba(56, 189, 248, 0.55);
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.2), 0 8px 28px rgba(0, 0, 0, 0.4);
}

.graph-zoom-stack {
  position: absolute;
  bottom: 108px;
  right: 20px;
  z-index: 11;
  display: flex;
  flex-direction: column;
  gap: 6px;
  pointer-events: none;
}

.zoom-btn {
  pointer-events: auto;
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 10px;
  border: 1px solid rgba(99, 102, 241, 0.4);
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
  transition: border-color 0.2s, color 0.2s, transform 0.15s;
}

.zoom-btn:hover {
  border-color: rgba(56, 189, 248, 0.55);
  color: #f8fafc;
}

.zoom-btn:active {
  transform: scale(0.96);
}

.zoom-btn-fit {
  font-size: 15px;
}

.graph-container {
  width: 100%;
  height: 100%;
}

.graph-view, .graph-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.graph-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #94a3b8;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.2;
}

/* Entity Types Legend - Bottom Left */
.graph-legend {
  position: absolute;
  bottom: 24px;
  left: 24px;
  padding: 14px 18px;
  border-radius: 12px;
  z-index: 10;
  background: rgba(15, 23, 42, 0.82);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(99, 102, 241, 0.28);
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.35),
    0 12px 40px rgba(0, 0, 0, 0.45),
    0 0 60px rgba(56, 189, 248, 0.06);
}

.legend-title {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  max-width: 320px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #e2e8f0;
}

.legend-dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.2);
}

.legend-label {
  white-space: nowrap;
}

.legend-count {
  opacity: 0.65;
  font-weight: 500;
  font-size: 11px;
}

/* Edge Labels Toggle - Top Right */
.edge-labels-toggle {
  position: absolute;
  top: 52px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(15, 23, 42, 0.82);
  backdrop-filter: blur(12px);
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(99, 102, 241, 0.3);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
  z-index: 10;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(51, 65, 85, 0.9);
  border-radius: 22px;
  transition: 0.3s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: #f8fafc;
  border-radius: 50%;
  transition: 0.3s;
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
}

input:checked + .slider {
  background: linear-gradient(90deg, #6366f1, #38bdf8);
}

input:checked + .slider:before {
  transform: translateX(18px);
}

.toggle-label {
  font-size: 12px;
  color: #cbd5e1;
  font-weight: 500;
}

/* Detail Panel - Right Side */
.detail-panel {
  position: absolute;
  backdrop-filter: blur(10px);
  background: rgba(10, 10, 15, 0.95);
  border: 1px solid var(--accent);
  box-shadow: var(--accent-glow);
  clip-path: polygon(0 0, calc(100% - 15px) 0, 100% 15px, 100% 100%, 15px 100%, 0 calc(100% - 15px));
  top: 60px;
  right: 20px;
  width: 320px;
  max-height: calc(100% - 100px);
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  overflow: hidden;
  font-family: var(--font-body);
  font-size: 13px;
  z-index: 20;
  display: flex;
  flex-direction: column;
}

.detail-panel-header {
  display: flex;
  background: rgba(0, 240, 255, 0.05);
  border-bottom: 1px solid var(--accent);
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: transparent;
  border-bottom: 1px solid var(--card-border);
  flex-shrink: 0;
}

.detail-title {
  font-weight: 600;
  color: var(--foreground);
  font-size: 14px;
}

.detail-type-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  margin-left: auto;
  margin-right: 12px;
}

.detail-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--text-muted);
  line-height: 1;
  padding: 0;
  transition: color 0.2s;
}

.detail-close:hover {
  color: var(--foreground);
}

.detail-content {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.detail-row {
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.detail-label {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  min-width: 80px;
}

.detail-value {
  color: var(--foreground);
  flex: 1;
  word-break: break-word;
}

.detail-value.uuid-text {
  font-family: var(--font-accent);
  font-size: 11px;
  color: var(--text-muted);
}

.detail-value.fact-text {
  line-height: 1.5;
  color: var(--text-muted);
}

.detail-section {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #F0F0F0;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 10px;
}

.properties-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.property-item {
  display: flex;
  gap: 8px;
}

.property-key {
  color: var(--text-muted);
  font-weight: 500;
  min-width: 90px;
}

.property-value {
  color: var(--foreground);
  flex: 1;
}

.summary-text {
  line-height: 1.6;
  color: var(--text-muted);
  font-size: 12px;
}

.labels-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.label-tag {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(0,0,0,0.5);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  font-size: 11px;
  color: var(--text-muted);
}

.episodes-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.episode-tag {
  display: inline-block;
  padding: 6px 10px;
  background: transparent;
  border: 1px solid #E8E8E8;
  border-radius: 6px;
  font-family: var(--font-accent);
  font-size: 10px;
  color: var(--text-muted);
  word-break: break-all;
}

/* Edge relation header */
.edge-relation-header {
  background: transparent;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--foreground);
  line-height: 1.5;
  word-break: break-word;
}

/* Building hint */
.graph-building-hint {
  position: absolute;
  bottom: 160px; /* Moved up from 80px */
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(8px);
  color: #fff;
  padding: 10px 20px;
  border-radius: 30px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-weight: 500;
  letter-spacing: 0.5px;
  z-index: 100;
}

.memory-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  animation: breathe 2s ease-in-out infinite;
}

.memory-icon {
  width: 18px;
  height: 18px;
  color: #4CAF50;
}

@keyframes breathe {
  0%, 100% { opacity: 0.7; transform: scale(1); filter: drop-shadow(0 0 2px rgba(76, 175, 80, 0.3)); }
  50% { opacity: 1; transform: scale(1.15); filter: drop-shadow(0 0 8px rgba(76, 175, 80, 0.6)); }
}

/* 시뮬레이션 종료 안내 스타일 */
.graph-building-hint.finished-hint {
  background: rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.finished-hint .hint-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.finished-hint .hint-icon {
  width: 18px;
  height: 18px;
  color: var(--card);
}

.finished-hint .hint-text {
  flex: 1;
  white-space: nowrap;
}

.hint-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: var(--card);
  transition: all 0.2s;
  margin-left: 8px;
  flex-shrink: 0;
}

.hint-close-btn:hover {
  background: rgba(255, 255, 255, 0.35);
  transform: scale(1.1);
}

/* Loading spinner */
.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(51, 65, 85, 0.8);
  border-top-color: #38bdf8;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
  box-shadow: 0 0 24px rgba(56, 189, 248, 0.25);
}

/* Self-loop styles */
.self-loop-header {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0,0,0,0.5);
  border: 1px solid var(--card-border);
}

.self-loop-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.8);
  padding: 2px 8px;
  border-radius: 10px;
}

.self-loop-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.self-loop-item {
  background: transparent;
  border: 1px solid var(--card-border);
  border-radius: 8px;
}

.self-loop-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(0,0,0,0.5);
  cursor: pointer;
  transition: background 0.2s;
}

.self-loop-item-header:hover {
  background: var(--card-border)EEE;
}

.self-loop-item.expanded .self-loop-item-header {
  background: #E8E8E8;
}

.self-loop-index {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--card-border);
  padding: 2px 6px;
  border-radius: 4px;
}

.self-loop-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--foreground);
  flex: 1;
}

.self-loop-toggle {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--card-border);
  border-radius: 4px;
  transition: all 0.2s;
}

.self-loop-item.expanded .self-loop-toggle {
  background: #D0D0D0;
  color: var(--text-muted);
}

.self-loop-item-content {
  padding: 12px;
  border-top: 1px solid var(--card-border);
}

.self-loop-item-content .detail-row {
  margin-bottom: 8px;
}

.self-loop-item-content .detail-label {
  font-size: 11px;
  min-width: 60px;
}

.self-loop-item-content .detail-value {
  font-size: 12px;
}

.self-loop-episodes {
  margin-top: 8px;
}

.episodes-list.compact {
  flex-direction: row;
  flex-wrap: wrap;
  gap: 4px;
}

.episode-tag.small {
  padding: 3px 6px;
  font-size: 9px;
}
</style>
