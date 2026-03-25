/**
 * 업로드 예정 파일과 시뮬레이션 요구사항을 임시 저장합니다.
 * 홈에서 엔진 시작 직후 화면 전환을 위해 사용하며,
 * 실제 API 호출은 Process 페이지에서 수행합니다.
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  maxAgents: null,
  isPending: false
})

export function setPendingUpload(files, requirement, maxAgents = null) {
  state.files = files
  state.simulationRequirement = requirement
  state.maxAgents = maxAgents
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    maxAgents: state.maxAgents,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.maxAgents = null
  state.isPending = false
}

export default state
