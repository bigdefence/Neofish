<template>
  <router-view />
</template>

<script setup>
// Vue Router로 페이지를 관리합니다.
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Share+Tech+Mono&family=Fira+Code:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap');

:root {
  --bg-color: #0a0a0f;
  --bg-color-alpha: rgba(10, 10, 15, 0.85);
  --glass-bg: rgba(19, 19, 20, 0.6);
  --glass-border: rgba(0, 240, 255, 0.15);
  --glass-glow: 0 0 20px rgba(0, 240, 255, 0.05);

  --accent: #00f0ff;
  --accent-glow: 0 0 10px rgba(0, 240, 255, 0.5), 0 0 20px rgba(0, 240, 255, 0.3);
  --secondary: #a855f7;
  --secondary-glow: 0 0 10px rgba(168, 85, 247, 0.5);
  --warning: #ff2a2a;
  
  --foreground: #e0e0e0;
  --text-muted: #8b8b99;
  
  --font-heading: 'Orbitron', 'Space Grotesk', sans-serif;
  --font-body: 'Fira Code', 'JetBrains Mono', monospace;
  --font-accent: 'Share Tech Mono', monospace;

  --card: rgba(15, 15, 20, 0.9);
  --card-border: #1f1f2e;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  background-color: var(--bg-color) !important;
  color: var(--foreground);
  font-family: var(--font-body);
  /* Full page grid background */
  background-image: 
    linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
  background-size: 30px 30px;
  background-attachment: fixed;
  overflow-x: hidden;
}

#app {
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Cyberpunk Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
  background: var(--bg-color);
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.5);
  border-left: 1px solid var(--card-border);
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 240, 255, 0.2);
  border: 1px solid var(--accent);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--accent);
  box-shadow: var(--accent-glow);
}

button {
  font-family: inherit;
}
</style>
