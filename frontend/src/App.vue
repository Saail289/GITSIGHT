<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import api from './services/api.js'
import { useAuth } from './composables/useAuth.js'
import { useChatHistory } from './composables/useChatHistory.js'
import MaintenancePage from './views/MaintenancePage.vue'

// Maintenance Mode Check
const isMaintenanceMode = import.meta.env.VITE_MAINTENANCE_MODE === 'true'

// ========================================
// AUTH & CHAT HISTORY
// ========================================
const { 
  user, 
  isAuthenticated, 
  userDisplayName, 
  userAvatar, 
  loading: authLoading,
  signInWithGoogle, 
  signOut,
  initAuth 
} = useAuth()

const {
  sessions,
  sortedSessions,
  currentSessionId,
  loadingSessions,
  loadSessions,
  createSession,
  saveMessage,
  loadMessages,
  switchSession,
  deleteSession,
  clearCurrentSession
} = useChatHistory()

// ========================================
// STATE MANAGEMENT
// ========================================

// View State
const currentView = ref('landing') // 'landing' | 'chat'

// Chat State
const repoUrl = ref('')
const question = ref('')
const messages = ref([])
const isIngesting = ref(false)
const isQuerying = ref(false)
const isIngested = ref(false)
const currentRepoUrl = ref('')
const apiHealthy = ref(false)
const sidebarCollapsed = ref(false)
const selectedModel = ref('nemotron') // 'nemotron' | 'gpt-oss'

// UI Refs
const messageListRef = ref(null)

// Code snippets for background animation
const codeSnippets = [
  'git commit -m "feat: init"',
  'const repo = await fetch()',
  'function analyze() {}',
  'npm install gitsight',
  'git push origin main',
  'export default RAG',
  'async function embed()',
  'git merge feature/ai',
  'return vectors.search()',
  'class Repository {}',
  '// TODO: optimize',
  'git checkout -b dev',
  'await db.connect()',
  'const chunks = split()',
  'git pull --rebase',
]

// ========================================
// COMPUTED
// ========================================

const canSubmitRepo = computed(() => repoUrl.value.trim() && !isIngesting.value)
const canSubmitQuestion = computed(() => question.value.trim() && isIngested.value && !isQuerying.value)

// ========================================
// LIFECYCLE
// ========================================

onMounted(async () => {
  const result = await api.healthCheck()
  apiHealthy.value = result.success
  
  // Initialize auth and load chat history if authenticated
  await initAuth()
  if (isAuthenticated.value) {
    await loadSessions()
  }
})

// Watch for auth changes to load/clear chat history
watch(isAuthenticated, async (authenticated) => {
  if (authenticated) {
    await loadSessions()
  } else {
    // Clear local chat sessions when logged out
  }
})

// ========================================
// METHODS
// ========================================

// View Navigation
const enterChat = () => {
  currentView.value = 'chat'
  if (apiHealthy.value) {
    addSystemMessage('✓ Connected to GITSIGHT API')
  } else {
    addSystemMessage('⚠ API connection failed. Please ensure the backend is running.')
  }
}

const goToLanding = () => {
  currentView.value = 'landing'
}

// Message Helpers
const addSystemMessage = (text) => {
  messages.value.push({ type: 'system', text, id: Date.now() })
  scrollToBottom()
}

const addUserMessage = (text) => {
  messages.value.push({ type: 'user', text, id: Date.now() })
  scrollToBottom()
}

const addAIMessage = (text) => {
  messages.value.push({ type: 'ai', text, id: Date.now() })
  scrollToBottom()
}

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

// Repository Ingestion
const handleIngestRepo = async () => {
  if (!canSubmitRepo.value) return

  const url = repoUrl.value.trim()
  addUserMessage(`Analyze repository: ${url}`)
  addSystemMessage('⏳ Fetching and processing repository...')

  isIngesting.value = true

  try {
    const result = await api.ingestRepository(url)

    if (result.success) {
      isIngested.value = true
      currentRepoUrl.value = url
      addSystemMessage(`✓ Repository ingested successfully!`)
      
      // Create a new chat session for authenticated users
      if (isAuthenticated.value) {
        const repoName = url.split('/').slice(-2).join('/')
        await createSession(url, `Chat - ${repoName}`)
      }
      
      addAIMessage(`I've analyzed **${url}**. I found ${result.data?.chunks_processed || 'multiple'} content chunks including code, documentation, and README files.\n\nAsk me anything about this repository!`)
    } else {
      addSystemMessage(`✗ Failed: ${result.error}`)
    }
  } catch (error) {
    addSystemMessage(`✗ Error: ${error.message}`)
  } finally {
    isIngesting.value = false
  }
}

// Question Handling
const handleAskQuestion = async () => {
  if (!canSubmitQuestion.value) return

  const q = question.value.trim()
  question.value = ''
  addUserMessage(q)
  
  // Save user message to database if authenticated
  if (isAuthenticated.value && currentSessionId.value) {
    await saveMessage('user', q)
  }

  isQuerying.value = true

  try {
    const result = await api.queryRepository(currentRepoUrl.value, q, selectedModel.value)

    if (result.success) {
      const answer = result.data?.answer || 'I found relevant information but couldn\'t generate a response.'
      addAIMessage(answer)
      
      // Save AI response to database if authenticated
      if (isAuthenticated.value && currentSessionId.value) {
        await saveMessage('ai', answer)
      }
    } else {
      addSystemMessage(`✗ Query failed: ${result.error}`)
    }
  } catch (error) {
    addSystemMessage(`✗ Error: ${error.message}`)
  } finally {
    isQuerying.value = false
  }
}

// Reset
const resetChat = () => {
  messages.value = []
  isIngested.value = false
  currentRepoUrl.value = ''
  repoUrl.value = ''
  question.value = ''
  clearCurrentSession()
  if (apiHealthy.value) {
    addSystemMessage('✓ Connected to GITSIGHT API')
  }
}

// Start new chat (with session creation for authenticated users)
const startNewChat = async () => {
  resetChat()
  if (isAuthenticated.value && currentRepoUrl.value) {
    await createSession(currentRepoUrl.value)
  }
}

// Load a previous chat session
const loadChatSession = async (session) => {
  messages.value = []
  currentRepoUrl.value = session.repo_url
  isIngested.value = true
  
  const sessionMessages = await switchSession(session.id)
  
  // Convert database messages to local format
  for (const msg of sessionMessages) {
    messages.value.push({
      type: msg.role,
      text: msg.content,
      id: msg.id
    })
  }
  
  scrollToBottom()
}

// Delete a chat session
const handleDeleteSession = async (sessionId) => {
  await deleteSession(sessionId)
}

// Toggle Sidebar
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// Handle Google Sign In
const handleGoogleSignIn = async () => {
  await signInWithGoogle()
}

// Handle Sign Out
const handleSignOut = async () => {
  await signOut()
  resetChat()
}
</script>

<template>
  <!-- Maintenance Mode -->
  <MaintenancePage v-if="isMaintenanceMode" />
  
  <!-- Normal App -->
  <template v-else>
  <!-- ========================================
       ANIMATED BACKGROUND (Shared)
       ======================================== -->
  <div class="matrix-bg">
    <div class="particle-grid"></div>
    
    <!-- Floating Code Snippets -->
    <div 
      v-for="(snippet, i) in codeSnippets" 
      :key="i"
      class="code-float"
      :style="{
        left: `${(i * 7) % 100}%`,
        animationDelay: `${i * 1.2}s`,
        fontSize: `${10 + (i % 4)}px`
      }"
    >
      {{ snippet }}
    </div>

    <!-- Git Branch Lines -->
    <div 
      v-for="n in 8" 
      :key="'branch-' + n"
      class="git-branch"
      :style="{
        left: `${n * 12}%`,
        top: `${(n * 15) % 80}%`,
        animationDelay: `${n * 0.8}s`
      }"
    ></div>

    <!-- Commit Dots -->
    <div 
      v-for="n in 12" 
      :key="'commit-' + n"
      class="commit-dot"
      :style="{
        left: `${(n * 8.5) % 95}%`,
        top: `${(n * 7.3) % 90}%`,
        animationDelay: `${n * 0.5}s`
      }"
    ></div>

    <div class="scanline"></div>
    <div class="bg-overlay"></div>
  </div>

  <!-- ========================================
       LANDING PAGE VIEW
       ======================================== -->
  <div v-if="currentView === 'landing'" class="landing-page">
    <div class="landing-content">
      <!-- Logo -->
      <div class="logo-section">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 3L4 7v10l8 4 8-4V7l-8-4z"/>
            <path d="M12 12L4 7"/>
            <path d="M12 12l8-5"/>
            <path d="M12 12v9"/>
            <circle cx="12" cy="12" r="2"/>
          </svg>
        </div>
        <h1 class="logo-text">GITSIGHT</h1>
        <div class="logo-tagline">AI-Powered Repository Intelligence</div>
      </div>

      <!-- Hero -->
      <div class="hero-section">
        <h2 class="hero-title">
          Understand Any GitHub Repository
          <span class="typing-cursor"></span>
        </h2>
        <p class="hero-description">
          Paste a repository URL and instantly chat with the codebase. 
          GITSIGHT uses advanced RAG technology to analyze code, docs, 
          and README files, giving you intelligent answers in seconds.
        </p>
      </div>

      <!-- Features -->
      <div class="features-grid">
        <div class="feature-card glass-panel">
          <div class="feature-icon">⚡</div>
          <h3>Instant Analysis</h3>
          <p>Deep-dive into any public repository in seconds</p>
        </div>
        <div class="feature-card glass-panel">
          <div class="feature-icon">🧠</div>
          <h3>AI-Powered</h3>
          <p>Natural language queries powered by LLM + RAG</p>
        </div>
        <div class="feature-card glass-panel">
          <div class="feature-icon">📚</div>
          <h3>Full Context</h3>
          <p>Understands code, docs, README, and structure</p>
        </div>
      </div>

      <!-- CTA -->
      <div class="cta-section">
        <!-- Not logged in: show sign-in first -->
        <div v-if="!isAuthenticated" class="landing-auth">
          <button 
            class="btn-google-landing" 
            @click="handleGoogleSignIn"
            :disabled="authLoading"
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            {{ authLoading ? 'Signing in...' : 'Sign in with Google to continue' }}
          </button>
          <p class="landing-auth-hint">Sign in required to use GITSIGHT</p>
        </div>

        <!-- Logged in: show welcome + launch -->
        <template v-else>
          <div class="landing-user">
            <img v-if="userAvatar" :src="userAvatar" :alt="userDisplayName" class="landing-avatar" />
            <span class="landing-welcome">Welcome, {{ userDisplayName }}</span>
          </div>
          <button class="btn-primary" @click="enterChat">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            Launch GITSIGHT
          </button>
        </template>

        <div class="api-status" :class="{ healthy: apiHealthy }">
          <span class="status-dot"></span>
          {{ apiHealthy ? 'API Online' : 'API Offline' }}
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================
       CHAT VIEW
       ======================================== -->
  <div v-else class="chat-view">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="sidebar-logo" @click="goToLanding">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 3L4 7v10l8 4 8-4V7l-8-4z"/>
            <circle cx="12" cy="12" r="2"/>
          </svg>
          <span v-if="!sidebarCollapsed">GITSIGHT</span>
        </div>
        <button class="toggle-btn" @click="toggleSidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="sidebarCollapsed" d="M9 18l6-6-6-6"/>
            <path v-else d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
      </div>

      <div class="sidebar-content" v-if="!sidebarCollapsed">
        <!-- Repository Input -->
        <div class="repo-section">
          <label class="input-label">Repository URL</label>
          <div class="input-group">
            <input
              v-model="repoUrl"
              type="text"
              class="input-field"
              placeholder="https://github.com/user/repo"
              :disabled="isIngesting"
              @keyup.enter="handleIngestRepo"
            />
            <button 
              class="btn-secondary" 
              @click="handleIngestRepo"
              :disabled="!canSubmitRepo"
            >
              {{ isIngesting ? '...' : 'Analyze' }}
            </button>
          </div>
        </div>

        <!-- Current Repo Info -->
        <div v-if="isIngested" class="repo-info glass-panel">
          <div class="repo-status">
            <span class="status-dot active"></span>
            Active Repository
          </div>
          <div class="repo-name">{{ currentRepoUrl.split('/').slice(-2).join('/') }}</div>
          <button class="btn-secondary reset-btn" @click="resetChat">
            Clear & Reset
          </button>
        </div>

        <!-- User Profile / Auth Section -->
        <div class="auth-section">
          <div v-if="isAuthenticated" class="user-profile glass-panel">
            <img 
              v-if="userAvatar" 
              :src="userAvatar" 
              :alt="userDisplayName"
              class="user-avatar"
            />
            <div v-else class="user-avatar-placeholder">
              {{ userDisplayName?.charAt(0)?.toUpperCase() || '?' }}
            </div>
            <div class="user-info">
              <div class="user-name">{{ userDisplayName }}</div>
              <button class="btn-link" @click="handleSignOut">Sign out</button>
            </div>
          </div>
          <div v-else class="login-prompt glass-panel">
            <button 
              class="btn-google" 
              @click="handleGoogleSignIn"
              :disabled="authLoading"
            >
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              {{ authLoading ? 'Signing in...' : 'Sign in with Google' }}
            </button>
            <p class="login-hint">Sign in to save chat history</p>
          </div>
        </div>

        <!-- Chat History Section (only for authenticated users) -->
        <div v-if="isAuthenticated" class="history-section">
          <div class="history-header">
            <h4>💬 Chat History</h4>
            <button v-if="isIngested" class="btn-new-chat" @click="startNewChat" title="Start new chat">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
            </button>
          </div>
          
          <div v-if="loadingSessions" class="history-loading">
            Loading...
          </div>
          
          <div v-else-if="sortedSessions.length === 0" class="history-empty">
            <p>No chat history yet</p>
          </div>
          
          <div v-else class="history-list">
            <div 
              v-for="session in sortedSessions.slice(0, 10)" 
              :key="session.id"
              class="history-item"
              :class="{ active: currentSessionId === session.id }"
              @click="loadChatSession(session)"
            >
              <div class="history-item-content">
                <div class="history-title">{{ session.title }}</div>
                <div class="history-repo">{{ session.repo_url.split('/').slice(-2).join('/') }}</div>
              </div>
              <button 
                class="history-delete" 
                @click.stop="handleDeleteSession(session.id)"
                title="Delete"
              >×</button>
            </div>
          </div>
        </div>

        <!-- Tips (show only for non-authenticated users) -->
        <div v-if="!isAuthenticated" class="tips-section">
          <h4>Quick Tips</h4>
          <ul>
            <li>Ask about functions, classes, or features</li>
            <li>Request code explanations</li>
            <li>Query project structure</li>
          </ul>
        </div>
      </div>

      <div class="sidebar-footer" v-if="!sidebarCollapsed">
        <div class="api-indicator" :class="{ online: apiHealthy }">
          <span class="indicator-dot"></span>
          {{ apiHealthy ? 'Connected' : 'Disconnected' }}
        </div>
      </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="chat-main">
      <!-- Messages -->
      <div class="message-list" ref="messageListRef">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">💬</div>
          <h3>Ready to explore</h3>
          <p>Enter a GitHub repository URL in the sidebar to begin</p>
        </div>

        <div 
          v-for="msg in messages" 
          :key="msg.id"
          class="message"
          :class="{
            'message-user': msg.type === 'user',
            'message-ai': msg.type === 'ai',
            'message-system': msg.type === 'system'
          }"
        >
          <div v-if="msg.type === 'ai'" class="message-avatar">
            <svg viewBox="0 0 24 24" fill="none" class="gitsight-icon">
              <path d="M12 3L4 7v10l8 4 8-4V7l-8-4z" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="12" cy="12" r="2.5" fill="currentColor"/>
            </svg>
          </div>
          <div class="message-content" v-html="formatMessage(msg.text)"></div>
        </div>

        <!-- Loading Indicator -->
        <div v-if="isQuerying" class="message message-ai">
          <div class="message-avatar">
            <svg viewBox="0 0 24 24" fill="none" class="gitsight-icon">
              <path d="M12 3L4 7v10l8 4 8-4V7l-8-4z" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="12" cy="12" r="2.5" fill="currentColor"/>
            </svg>
          </div>
          <div class="loading-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="chat-input-area">
        <div class="input-container glass-panel">
          <div class="model-selector">
            <select v-model="selectedModel" class="model-dropdown">
              <option value="nemotron">Nemotron 30B</option>
              <option value="gpt-oss">GPT-OSS 120B</option>
            </select>
          </div>
          <textarea
            v-model="question"
            class="chat-input"
            placeholder="Ask a question about the repository..."
            :disabled="!isIngested || isQuerying"
            @keydown.enter.exact.prevent="handleAskQuestion"
            rows="1"
          ></textarea>
          <button 
            class="send-btn"
            @click="handleAskQuestion"
            :disabled="!canSubmitQuestion"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 2L11 13"/>
              <path d="M22 2L15 22L11 13L2 9L22 2z"/>
            </svg>
          </button>
        </div>
      </div>
    </main>
  </div>
  </template>
</template>

<script>
// Format message with comprehensive markdown parsing
function formatMessage(text) {
  if (!text) return ''
  
  let result = text
  
  // Process fenced code blocks first (```language\ncode```)
  result = result.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
    const language = lang || 'code'
    const escapedCode = code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .trim()
    
    return `<div class="code-block-wrapper">
      <div class="code-block-header">
        <span class="code-language">${language}</span>
        <button class="copy-btn" onclick="navigator.clipboard.writeText(this.closest('.code-block-wrapper').querySelector('code').textContent).then(() => { this.textContent = 'Copied!'; setTimeout(() => this.textContent = 'Copy', 2000) })">Copy</button>
      </div>
      <pre class="code-block-content"><code>${escapedCode}</code></pre>
    </div>`
  })
  
  // Process markdown tables
  result = result.replace(/(\|[^\n]+\|\n)+/g, (tableMatch) => {
    const rows = tableMatch.trim().split('\n').filter(row => row.trim())
    if (rows.length < 2) return tableMatch
    
    // Check if second row is a separator (|---|---|)
    const separatorPattern = /^\|[\s-:|]+\|$/
    const hasSeparator = rows.length >= 2 && separatorPattern.test(rows[1].trim())
    
    let html = '<table class="md-table"><thead><tr>'
    
    // Parse header row
    const headerCells = rows[0].split('|').filter(cell => cell.trim() !== '')
    headerCells.forEach(cell => {
      html += `<th>${cell.trim()}</th>`
    })
    html += '</tr></thead><tbody>'
    
    // Parse data rows (skip separator if present)
    const startRow = hasSeparator ? 2 : 1
    for (let i = startRow; i < rows.length; i++) {
      const cells = rows[i].split('|').filter(cell => cell.trim() !== '')
      if (cells.length > 0) {
        html += '<tr>'
        cells.forEach(cell => {
          html += `<td>${cell.trim()}</td>`
        })
        html += '</tr>'
      }
    }
    
    html += '</tbody></table>'
    return html
  })
  
  // Process horizontal rules (--- or ***)
  result = result.replace(/^---+$/gm, '<hr class="md-hr">')
  result = result.replace(/^\*\*\*+$/gm, '<hr class="md-hr">')
  
  // Process blockquotes (> text)
  result = result.replace(/^>\s*(.*)$/gm, '<div class="md-blockquote">$1</div>')
  
  // Process headers (#### h4, ### h3, ## h2, # h1)
  result = result.replace(/^####\s+(.+)$/gm, '<h5 class="md-h4">$1</h5>')
  result = result.replace(/^###\s+(.+)$/gm, '<h4 class="md-h3">$1</h4>')
  result = result.replace(/^##\s+(.+)$/gm, '<h3 class="md-h2">$1</h3>')
  result = result.replace(/^#\s+(.+)$/gm, '<h2 class="md-h1">$1</h2>')
  
  // Process numbered lists (1. item, 2. item)
  result = result.replace(/^\d+\.\s+(.+)$/gm, '<li class="md-ordered-item">$1</li>')
  result = result.replace(/(<li class="md-ordered-item">.*<\/li>\n?)+/g, '<ol class="md-ordered-list">$&</ol>')
  
  // Process unordered lists (- item or * item)
  result = result.replace(/^[-*]\s+(.+)$/gm, '<li class="md-list-item">$1</li>')
  result = result.replace(/(<li class="md-list-item">.*<\/li>\n?)+/g, '<ul class="md-list">$&</ul>')
  
  // Process bold (**text**)
  result = result.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  
  // Process italic (*text* but not inside code)
  result = result.replace(/(?<![`])\*([^*\n]+)\*(?![`])/g, '<em>$1</em>')
  result = result.replace(/(?<![`])_([^_\n]+)_(?![`])/g, '<em>$1</em>')
  
  // Process inline code (`code`) - do this after other processing
  result = result.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>')
  
  // Process line breaks
  result = result.replace(/\n/g, '<br>')
  
  // Clean up extra breaks after block elements
  result = result.replace(/<\/div><br>/g, '</div>')
  result = result.replace(/<\/h[2345]><br>/g, (match) => match.replace('<br>', ''))
  result = result.replace(/<\/ul><br>/g, '</ul>')
  result = result.replace(/<\/ol><br>/g, '</ol>')
  result = result.replace(/<hr class="md-hr"><br>/g, '<hr class="md-hr">')
  result = result.replace(/<\/table><br>/g, '</table>')
  
  // Clean up consecutive blockquotes
  result = result.replace(/<\/div><br><div class="md-blockquote">/g, '</div><div class="md-blockquote">')
  
  return result
}

export default {
  methods: {
    formatMessage
  }
}
</script>

<style scoped>
/* ========================================
   LANDING PAGE STYLES
   ======================================== */

.landing-page {
  position: relative;
  z-index: 2;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.landing-content {
  max-width: 900px;
  text-align: center;
}

/* Logo Section */
.logo-section {
  margin-bottom: 48px;
}

.logo-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  color: var(--accent-primary);
  filter: drop-shadow(0 0 20px var(--accent-glow));
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.logo-text {
  font-family: var(--font-mono);
  font-size: 56px;
  font-weight: 700;
  letter-spacing: 12px;
  color: var(--accent-primary);
  text-shadow: var(--glow-strong);
  margin-bottom: 12px;
}

.logo-tagline {
  font-size: 16px;
  color: var(--text-secondary);
  letter-spacing: 4px;
  text-transform: uppercase;
}

/* Hero Section */
.hero-section {
  margin-bottom: 48px;
}

.hero-title {
  font-size: 32px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-primary);
}

.hero-description {
  font-size: 17px;
  color: var(--text-secondary);
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.8;
}

/* Features Grid */
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 48px;
}

.feature-card {
  padding: 28px 24px;
  text-align: center;
  transition: var(--transition-smooth);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--glow-subtle);
}

.feature-icon {
  font-size: 32px;
  margin-bottom: 16px;
}

.feature-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--accent-primary);
}

.feature-card p {
  font-size: 14px;
  color: var(--text-secondary);
}

/* CTA Section */
.cta-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.api-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.api-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff4444;
}

.api-status.healthy .status-dot {
  background: var(--accent-primary);
  box-shadow: 0 0 8px var(--accent-glow);
}

/* Landing Auth */
.landing-auth {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.btn-google-landing {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 28px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-smooth);
  backdrop-filter: blur(8px);
}

.btn-google-landing:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.35);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.btn-google-landing:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.landing-auth-hint {
  font-size: 13px;
  color: var(--text-muted);
}

.landing-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.landing-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid var(--accent-primary);
}

.landing-welcome {
  font-size: 14px;
  color: var(--accent-primary);
  font-family: var(--font-mono);
}

/* ========================================
   CHAT VIEW STYLES
   ======================================== */

.chat-view {
  position: relative;
  z-index: 2;
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* Sidebar */
.sidebar {
  width: 320px;
  background: rgba(10, 10, 10, 0.95);
  border-right: 1px solid rgba(0, 255, 65, 0.15);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(0, 255, 65, 0.1);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  color: var(--accent-primary);
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 2px;
}

.sidebar-logo svg {
  width: 24px;
  height: 24px;
}

.toggle-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  transition: var(--transition-smooth);
}

.toggle-btn:hover {
  color: var(--accent-primary);
}

.sidebar-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.repo-section {
  margin-bottom: 24px;
}

.input-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.input-group .input-field {
  font-size: 13px;
  padding: 12px 14px;
}

.repo-info {
  padding: 16px;
  margin-bottom: 24px;
}

.repo-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-dot.active {
  background: var(--accent-primary);
  box-shadow: 0 0 8px var(--accent-glow);
}

.repo-name {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--accent-primary);
  margin-bottom: 12px;
  word-break: break-all;
}

.reset-btn {
  width: 100%;
  padding: 8px;
  font-size: 12px;
}

.tips-section {
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 65, 0.1);
}

.tips-section h4 {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.tips-section ul {
  list-style: none;
  font-size: 13px;
  color: var(--text-muted);
}

.tips-section li {
  padding: 6px 0;
  padding-left: 16px;
  position: relative;
}

.tips-section li::before {
  content: '→';
  position: absolute;
  left: 0;
  color: var(--accent-secondary);
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 255, 65, 0.1);
}

.api-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ff4444;
}

.api-indicator.online .indicator-dot {
  background: var(--accent-primary);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Main Chat Area */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
}

.message-list {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 18px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 14px;
}

.message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message-avatar {
  font-size: 20px;
  flex-shrink: 0;
}

.message-content {
  flex: 1;
}

.message-content code {
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--accent-primary);
}

/* Chat Input */
.chat-input-area {
  padding: 20px 24px;
  border-top: 1px solid rgba(0, 255, 65, 0.1);
}

.model-selector {
  flex-shrink: 0;
}

.model-dropdown {
  background: rgba(0, 255, 65, 0.08);
  border: 1px solid rgba(0, 255, 65, 0.2);
  border-radius: 8px;
  color: var(--accent-primary);
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 6px 10px;
  cursor: pointer;
  transition: var(--transition-smooth);
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2300FF41' stroke-width='1.5' fill='none'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 26px;
}

.model-dropdown:hover {
  border-color: rgba(0, 255, 65, 0.5);
  background-color: rgba(0, 255, 65, 0.12);
}

.model-dropdown:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 8px rgba(0, 255, 65, 0.2);
}

.model-dropdown option {
  background: #0a0f0a;
  color: var(--text-primary);
  padding: 8px;
}

.input-container {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 8px 8px 20px;
}

.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 15px;
  resize: none;
  min-height: 24px;
  max-height: 120px;
}

.chat-input::placeholder {
  color: var(--text-muted);
}

.chat-input:focus {
  outline: none;
}

.chat-input:disabled {
  opacity: 0.5;
}

.send-btn {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-primary);
  border: none;
  border-radius: 8px;
  color: #000;
  cursor: pointer;
  transition: var(--transition-smooth);
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  box-shadow: var(--glow-subtle);
  transform: scale(1.05);
}

.send-btn:disabled {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    z-index: 100;
    transform: translateX(-100%);
  }

  .sidebar:not(.collapsed) {
    transform: translateX(0);
  }

  .logo-text {
    font-size: 36px;
    letter-spacing: 6px;
  }

  .hero-title {
    font-size: 24px;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>