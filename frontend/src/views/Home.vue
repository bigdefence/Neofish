<template>
  <div class="cyber-theme home-container relative">
    <!-- Scanline Overlay -->
    <div class="scanlines"></div>

    <!-- Circuit Pattern Background -->
    <div class="circuit-bg"></div>

    <!-- Navbar -->
    <nav class="cyber-navbar">
      <div class="nav-brand cyber-glitch" data-text="NEOFISH">
        NEO<span class="text-accent">FISH</span>
      </div>
      <div class="nav-links">
        <a href="https://github.com/666ghj/Neofish" target="_blank" class="cyber-link">
          [ SOURCE_CODE ] <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <!-- Top: Hero Section -->
      <section class="hero-section">
        <div class="hero-content">
          <div class="tag-row">
            <span class="cyber-badge">SYS.VER://0.1.0</span>
            <span class="status-indicator">
              <span class="cyber-dot"></span> LINK_ESTABLISHED
            </span>
          </div>
          
          <h1 class="main-title cyber-glitch-text" data-text="SIMULATE THE VOID">
            SIMULATE <br/>
            <span class="text-accent underline-glitch">THE VOID</span>
          </h1>
          
          <div class="hero-desc">
            <p>
              > INJECT UNSTRUCTURED DATA.<br>
              > INITIALIZE PARALLEL REALITY (CAP: 1,000,000 ENTITIES).<br>
              > OBSERVE EMERGENT BEHAVIORS.
            </p>
          </div>
        </div>
      </section>

      <!-- Layout -->
      <section class="console-layout">
        
        <!-- Left Intelligence Panel -->
        <div class="intelligence-panel">
          <div class="cyber-panel-header">
            <span class="panel-title">// SYSTEM_DIAGNOSTICS</span>
            <div class="cyber-line"></div>
          </div>

          <div class="metrics-grid">
            <div class="cyber-card">
              <div class="metric-label">COST_EFFICIENCY</div>
              <div class="metric-value text-accentTertiary glow-cyan">~$5.00</div>
              <div class="metric-sub">AVG/SIMULATION</div>
            </div>
            <div class="cyber-card">
              <div class="metric-label">MAX_CAPACITY</div>
              <div class="metric-value text-accentSecondary glow-magenta">1,000,000</div>
              <div class="metric-sub">ENTITIES</div>
            </div>
          </div>

          <div class="workflow-steps">
            <div class="workflow-item">
              <div class="step-num text-accentTertiary">01</div>
              <div class="step-content">
                <div class="step-title">GRAPH_BUILDING</div>
                <div class="step-desc">EXTRACT REALITY SEEDS -> GRAPHRAG</div>
              </div>
            </div>
            <div class="workflow-item">
              <div class="step-num text-accentTertiary">02</div>
              <div class="step-content">
                <div class="step-title">ENV_SETUP</div>
                <div class="step-desc">GENERATE PERSONAS & PARAMETERS</div>
              </div>
            </div>
            <div class="workflow-item">
              <div class="step-num text-accentSecondary">03</div>
              <div class="step-content">
                <div class="step-title">SIMULATION_RUN</div>
                <div class="step-desc">PARALLEL INTERACTIONS & MEMORIES</div>
              </div>
            </div>
            <div class="workflow-item">
              <div class="step-num text-accentSecondary">04</div>
              <div class="step-content">
                <div class="step-title">INSIGHTS_REPORTS</div>
                <div class="step-desc">DERIVE STRATEGIC CONCLUSIONS</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Command Console -->
        <div class="command-console cyber-card-terminal">
          <div class="terminal-header">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
            <span class="terminal-title">CMD.EXE - ROOT ACCESS</span>
          </div>

          <div class="terminal-body">
            <!-- Dropzone -->
            <div class="console-block">
              <div class="block-header">
                <span class="block-title">> UPLOAD_REALITY_SEED (.PDF/.MD/.TXT)</span>
              </div>
              
              <div 
                class="upload-zone cyber-inset bg-input"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />
                
                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon-wrapper">
                    <span class="upload-icon text-accentTertiary">⇪</span>
                  </div>
                  <div class="upload-text text-foreground">DRAG & DROP KNOWLEDGE FILES</div>
                  <div class="upload-subtext text-mutedForeground blink-text">_CLICK_TO_BROWSE</div>
                </div>
                
                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item cyber-dark-item">
                    <span class="file-icon text-accent">📄</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn text-destructive">[X]</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Prompt Input -->
            <div class="console-block">
              <div class="block-header">
                <span class="block-title">> SET_SIMULATION_DIRECTIVES</span>
              </div>
              <div class="cyber-input-wrapper">
                <span class="input-prefix text-accent">></span>
                <textarea
                  v-model="formData.simulationRequirement"
                  class="cyber-textarea bg-input"
                  placeholder="ENTER NATURAL LANGUAGE PREDICTION GOALS..."
                  rows="4"
                  :disabled="loading"
                ></textarea>
              </div>
            </div>

            <!-- Max Agents Input -->
            <div class="console-block">
              <div class="block-header">
                <span class="block-title">> OVERRIDE_MAX_AGENTS [OPTIONAL]</span>
              </div>
              <div class="cyber-input-wrapper cyber-flex">
                <span class="input-prefix text-accentSecondary">$</span>
                <input 
                  type="number" 
                  v-model.number="formData.maxAgents" 
                  class="cyber-input bg-input" 
                  placeholder="EX: 50" 
                  min="1"
                  :disabled="loading"
                />
                <span class="limit-hint text-mutedForeground">LEAVE BLANK = ALL ENTITIES</span>
              </div>
            </div>

            <!-- Start Button -->
            <div class="console-block start-block">
              <button 
                class="cyber-btn-primary"
                @click="startSimulation"
                :disabled="!canSubmit || loading"
              >
                <div class="btn-inner">
                  <span class="btn-text" v-if="!loading">EXECUTE_SIMULATION.SH</span>
                  <span class="btn-text cyber-glitch" data-text="BOOTING_SYSTEM..." v-else>BOOTING_SYSTEM...</span>
                  <span class="btn-cursor blink-text">_</span>
                </div>
              </button>
            </div>

          </div>
        </div>
      </section>

      <!-- History Database -->
      <HistoryDatabase class="mt-large cyber-history-override" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'

const router = useRouter()

const formData = ref({
  simulationRequirement: '',
  maxAgents: null
})

const files = ref([])
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== ''
})

const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

const handleDragOver = (e) => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = (e) => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return
  
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement, formData.value.maxAgents)
    
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style>
/* CYBERPUNK / GLITCH DESIGN SYSTEM IMPORTS */
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Orbitron:wght@500;700;900&family=Share+Tech+Mono&display=swap');

/* Base Body Application */
body {
  background-color: #0a0a0f !important;
  color: #e0e0e0 !important;
  margin: 0;
}
</style>

<style scoped>
/* Scoped System Design Variables */
.cyber-theme {
  --background: #0a0a0f;
  --foreground: #e0e0e0;
  --card: #12121a;
  --muted: #1c1c2e;
  --mutedForeground: #6b7280;
  
  --accent: #00ff88;
  --accentSecondary: #ff00ff;
  --accentTertiary: #00d4ff;
  
  --border-color: #2a2a3a;
  --input-bg: #12121a;
  --destructive: #ff3366;

  --neon-glow: 0 0 5px #00ff88, 0 0 10px #00ff8840;
  --neon-glow-lg: 0 0 10px #00ff88, 0 0 20px #00ff8860, 0 0 40px #00ff8830;
  --neon-secondary: 0 0 5px #ff00ff, 0 0 20px #ff00ff60;
  --neon-tertiary: 0 0 5px #00d4ff, 0 0 20px #00d4ff60;

  --font-heading: 'Orbitron', 'Share Tech Mono', sans-serif;
  --font-body: 'Fira Code', 'JetBrains Mono', monospace;
  --font-accent: 'Share Tech Mono', monospace;
}

/* Base Styles */
.home-container {
  min-height: 100vh;
  font-family: var(--font-body);
  background: var(--background);
  color: var(--foreground);
  overflow-x: hidden;
  z-index: 1;
}

/* Color Utils */
.text-accent { color: var(--accent); }
.text-accentSecondary { color: var(--accentSecondary); }
.text-accentTertiary { color: var(--accentTertiary); }
.text-foreground { color: var(--foreground); }
.text-mutedForeground { color: var(--mutedForeground); }
.text-destructive { color: var(--destructive); }
.bg-input { background: var(--input-bg); }

/* Glow Utils */
.glow-cyan { text-shadow: var(--neon-tertiary); }
.glow-magenta { text-shadow: var(--neon-secondary); }

/* Texture: Scanlines */
.scanlines {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.3) 2px,
    rgba(0, 0, 0, 0.3) 4px
  );
  pointer-events: none;
  z-index: 9999;
}

/* Texture: Circuit Grid */
.circuit-bg {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image:
    linear-gradient(rgba(0, 255, 136, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 255, 136, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: -1;
}

/* Navbar */
.cyber-navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 3rem;
  border-bottom: 1px solid var(--border-color);
  background: rgba(10, 10, 15, 0.8);
  backdrop-filter: blur(5px);
}

.nav-brand {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 1.5rem;
  letter-spacing: 0.15em;
}

.cyber-link {
  color: var(--mutedForeground);
  text-decoration: none;
  font-family: var(--font-accent);
  font-size: 0.9rem;
  transition: all 0.2s;
}

.cyber-link:hover {
  color: var(--accentSecondary);
  text-shadow: var(--neon-secondary);
}

/* Content Container */
.main-content {
  max-width: 1300px;
  margin: 0 auto;
  padding: 4rem 2rem;
}

/* Hero Section */
.hero-section {
  margin-bottom: 6rem;
  position: relative;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
  font-family: var(--font-accent);
}

.cyber-badge {
  background: rgba(0, 255, 136, 0.1);
  color: var(--accent);
  border: 1px solid var(--accent);
  padding: 0.3rem 0.8rem;
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  box-shadow: inset 0 0 5px rgba(0, 255, 136, 0.2);
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--foreground);
}

.cyber-dot {
  width: 8px;
  height: 8px;
  background-color: var(--accentTertiary);
  box-shadow: var(--neon-tertiary);
  animation: blink 2s steps(2, start) infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.main-title {
  font-family: var(--font-heading);
  font-size: 5rem;
  font-weight: 900;
  line-height: 1.1;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 1.5rem;
  color: var(--foreground);
}

.underline-glitch {
  border-bottom: 4px solid var(--accent);
  display: inline-block;
  box-shadow: 0 4px 10px rgba(0, 255, 136, 0.4);
}

.hero-desc {
  font-size: 1.1rem;
  line-height: 1.8;
  color: var(--mutedForeground);
  max-width: 600px;
  border-left: 2px solid var(--accentSecondary);
  padding-left: 1rem;
}

/* Glitch / Chromatic Aberration Text */
.cyber-glitch-text {
  position: relative;
  display: inline-block;
  text-shadow: -2px 0 var(--accentSecondary), 2px 0 var(--accentTertiary);
}

.cyber-glitch {
  position: relative;
}

.cyber-glitch::before, .cyber-glitch::after {
  content: attr(data-text);
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--background);
  color: var(--foreground);
  overflow: hidden;
  clip: rect(0, 900px, 0, 0); 
}

.cyber-glitch::before {
  left: -2px;
  text-shadow: 1px 0 var(--accentSecondary);
  animation: glitch-anim 3s infinite linear alternate-reverse;
}

.cyber-glitch::after {
  left: 2px;
  text-shadow: -1px 0 var(--accentTertiary);
  animation: glitch-anim-2 2.5s infinite linear alternate-reverse;
}

@keyframes glitch-anim {
  0% { clip: rect(24px, 9999px, 83px, 0); }
  20% { clip: rect(61px, 9999px, 14px, 0); }
  40% { clip: rect(78px, 9999px, 5px, 0); }
  60% { clip: rect(10px, 9999px, 93px, 0); }
  80% { clip: rect(35px, 9999px, 45px, 0); }
  100% { clip: rect(81px, 9999px, 20px, 0); }
}

@keyframes glitch-anim-2 {
  0% { clip: rect(65px, 9999px, 100px, 0); }
  20% { clip: rect(15px, 9999px, 80px, 0); }
  40% { clip: rect(35px, 9999px, 10px, 0); }
  60% { clip: rect(90px, 9999px, 30px, 0); }
  80% { clip: rect(20px, 9999px, 60px, 0); }
  100% { clip: rect(55px, 9999px, 40px, 0); }
}

/* Layout */
.console-layout {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 3rem;
  align-items: start;
}

/* Left Panel */
.cyber-panel-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.panel-title {
  font-family: var(--font-accent);
  font-size: 1rem;
  color: var(--accent);
  letter-spacing: 0.1em;
}

.cyber-line {
  flex: 1;
  height: 1px;
  background: var(--border-color);
  position: relative;
}
.cyber-line::before {
  content: '';
  position: absolute;
  left: 0; top: -1px;
  width: 30%; height: 3px;
  background: var(--accent);
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.cyber-card {
  background: var(--card);
  border: 1px solid var(--border-color);
  padding: 1.5rem;
  position: relative;
  clip-path: polygon(
    0 15px, 15px 0, 
    100% 0, 100% calc(100% - 15px), 
    calc(100% - 15px) 100%, 0 100%
  );
  transition: all 0.3s;
}

.cyber-card:hover {
  border-color: var(--accentTertiary);
  box-shadow: inset 0 0 10px rgba(0, 212, 255, 0.1);
  transform: translateY(-2px);
}

.metric-label {
  font-family: var(--font-accent);
  font-size: 0.75rem;
  color: var(--mutedForeground);
  margin-bottom: 0.5rem;
  letter-spacing: 0.1em;
}

.metric-value {
  font-family: var(--font-heading);
  font-size: 2.2rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.metric-sub {
  font-family: var(--font-accent);
  font-size: 0.8rem;
  color: var(--mutedForeground);
}

/* Workflow Steps */
.workflow-steps {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  background: var(--muted);
  padding: 1rem;
  border-left: 2px solid var(--border-color);
  transition: border-color 0.3s;
}

.workflow-item:hover {
  border-left-color: var(--accent);
}

.step-num {
  font-family: var(--font-heading);
  font-size: 1.5rem;
  font-weight: 700;
  width: 2.5rem;
  margin-right: 1rem;
}

.step-title {
  font-family: var(--font-accent);
  font-weight: 600;
  font-size: 1rem;
  margin-bottom: 0.25rem;
  color: var(--foreground);
}

.step-desc {
  font-size: 0.85rem;
  color: var(--mutedForeground);
}

/* Right Command Console */
.cyber-card-terminal {
  background: var(--background);
  border: 1px solid var(--border-color);
  clip-path: polygon(
    0 10px, 10px 0, 
    100% 0, 100% calc(100% - 10px), 
    calc(100% - 10px) 100%, 0 100%
  );
}

.terminal-header {
  background: #171721;
  padding: 0.5rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-bottom: 1px solid var(--border-color);
}

.dot {
  width: 10px; height: 10px; border-radius: 50%;
}
.dot.red { background: var(--destructive); }
.dot.yellow { background: #ffcc00; }
.dot.green { background: var(--accent); }

.terminal-title {
  margin-left: 1rem;
  font-family: var(--font-accent);
  font-size: 0.8rem;
  color: var(--mutedForeground);
}

.terminal-body {
  padding: 2.5rem;
  background: var(--background);
}

.console-block {
  margin-bottom: 2.5rem;
}

.block-header {
  margin-bottom: 1rem;
}

.block-title {
  font-family: var(--font-accent);
  font-size: 0.95rem;
  color: var(--foreground);
  font-weight: 600;
}

/* Insets and Inputs */
.cyber-inset {
  border: 1px solid var(--border-color);
  padding: 1.5rem;
  position: relative;
}

.cyber-inset::before {
  content: ''; position: absolute; top:0; left:0; width:8px; height:8px;
  border-top: 1px solid var(--accent); border-left: 1px solid var(--accent);
}
.cyber-inset::after {
  content: ''; position: absolute; bottom:0; right:0; width:8px; height:8px;
  border-bottom: 1px solid var(--accentTertiary); border-right: 1px solid var(--accentTertiary);
}

.upload-zone {
  text-align: center;
  transition: all 0.3s;
  cursor: pointer;
  background: rgba(18, 18, 26, 0.5);
}
.upload-zone:hover, .upload-zone.drag-over {
  border-color: var(--accent);
  background: rgba(0, 255, 136, 0.05);
}

.upload-icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 1rem;
}
.upload-text {
  font-family: var(--font-accent);
  margin-bottom: 0.5rem;
}

.cyber-input-wrapper {
  display: flex;
  align-items: flex-start;
  border: 1px solid var(--border-color);
  background: var(--input-bg);
  padding: 0.5rem 1rem;
  transition: all 0.2s;
}

.cyber-input-wrapper:focus-within {
  border-color: var(--accent);
  box-shadow: inset 0 0 10px rgba(0, 255, 136, 0.1);
}

.cyber-flex {
  align-items: center;
}

.input-prefix {
  font-family: var(--font-accent);
  font-weight: bold;
  margin-top: 0.8rem;
  margin-right: 0.5rem;
}

.cyber-flex .input-prefix {
  margin-top: 0;
}

.cyber-textarea, .cyber-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--foreground);
  font-family: var(--font-body);
  font-size: 1rem;
  padding: 0.8rem 0;
  resize: vertical;
  outline: none;
}
.cyber-textarea::placeholder, .cyber-input::placeholder {
  color: var(--mutedForeground);
}
.limit-hint {
  font-family: var(--font-accent);
  font-size: 0.85rem;
}

/* Button */
.cyber-btn-primary {
  width: 100%;
  background: transparent;
  border: 2px solid var(--accent);
  color: var(--accent);
  font-family: var(--font-accent);
  font-size: 1.1rem;
  font-weight: bold;
  cursor: pointer;
  position: relative;
  transition: all 0.2s steps(4);
  clip-path: polygon(
    0 10px, 10px 0, 
    100% 0, 100% calc(100% - 10px), 
    calc(100% - 10px) 100%, 0 100%
  );
}

.btn-inner {
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cyber-btn-primary:not(:disabled):hover {
  background: var(--accent);
  color: var(--background);
  box-shadow: var(--neon-glow);
}

.cyber-btn-primary:not(:disabled):hover .btn-arrow,
.cyber-btn-primary:not(:disabled):hover .text-accent {
  color: var(--background);
}

.cyber-btn-primary:disabled {
  opacity: 0.3;
  border-color: var(--border-color);
  color: var(--mutedForeground);
  cursor: not-allowed;
}

.blink-text {
  animation: blink-text 1s step-end infinite;
}
@keyframes blink-text {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.file-item {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  margin-top: 0.5rem;
  border: 1px dashed var(--border-color);
  background: var(--muted);
}
.file-name {
  flex: 1;
  text-align: left;
  margin: 0 1rem;
  font-family: var(--font-accent);
  font-size: 0.9rem;
}
.remove-btn {
  background: none; border: none; font-family: var(--font-accent); cursor: pointer; font-weight: bold;
}
.remove-btn:hover {
  text-shadow: 0 0 5px var(--destructive);
}

/* History Data Overrides */
:deep(.history-container) {
  margin-top: 5rem;
  border-top: 1px dashed var(--border-color);
  background: transparent;
  padding-top: 2rem;
}
:deep(.history-container h2) {
  font-family: var(--font-heading);
  color: var(--foreground);
  text-transform: uppercase;
}
:deep(.project-card) {
  background: var(--card);
  border: 1px solid var(--border-color);
  clip-path: polygon(0 10px, 10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%);
  color: var(--foreground);
}
:deep(.project-card:hover) {
  border-color: var(--accentTertiary);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
}

@media (max-width: 1024px) {
  .console-layout {
    grid-template-columns: 1fr;
  }
}
</style>
