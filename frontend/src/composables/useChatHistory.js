/**
 * Chat History Composable
 * Manages chat sessions and messages with Supabase persistence
 */
import { ref, computed } from 'vue'
import { supabase } from '../supabase'

// Shared reactive state
const sessions = ref([])
const currentSessionId = ref(null)
const loadingSessions = ref(false)
const savingMessage = ref(false)

export function useChatHistory() {
    const currentSession = computed(() => {
        return sessions.value.find(s => s.id === currentSessionId.value) || null
    })

    const sortedSessions = computed(() => {
        return [...sessions.value].sort((a, b) =>
            new Date(b.updated_at) - new Date(a.updated_at)
        )
    })

    // Load all sessions for the current user
    async function loadSessions() {
        try {
            loadingSessions.value = true

            const { data, error } = await supabase
                .from('chat_sessions')
                .select('*')
                .order('updated_at', { ascending: false })

            if (error) {
                console.error('Error loading sessions:', error)
                return { data: null, error }
            }

            sessions.value = data || []
            return { data, error: null }
        } catch (err) {
            console.error('Load sessions exception:', err)
            return { data: null, error: err }
        } finally {
            loadingSessions.value = false
        }
    }

    // Create a new chat session
    async function createSession(repoUrl, title = null) {
        try {
            const { data: { user } } = await supabase.auth.getUser()

            if (!user) {
                console.warn('No user logged in, session not saved')
                return { data: null, error: new Error('Not authenticated') }
            }

            const sessionTitle = title || `Chat - ${new Date().toLocaleDateString()}`

            const { data, error } = await supabase
                .from('chat_sessions')
                .insert({
                    user_id: user.id,
                    repo_url: repoUrl,
                    title: sessionTitle
                })
                .select()
                .single()

            if (error) {
                console.error('Error creating session:', error)
                return { data: null, error }
            }

            sessions.value.unshift(data)
            currentSessionId.value = data.id

            return { data, error: null }
        } catch (err) {
            console.error('Create session exception:', err)
            return { data: null, error: err }
        }
    }

    // Save a message to the current session
    async function saveMessage(role, content, sessionId = null) {
        try {
            savingMessage.value = true
            const targetSessionId = sessionId || currentSessionId.value

            if (!targetSessionId) {
                console.warn('No active session, message not saved')
                return { data: null, error: new Error('No active session') }
            }

            const { data, error } = await supabase
                .from('chat_messages')
                .insert({
                    session_id: targetSessionId,
                    role,
                    content
                })
                .select()
                .single()

            if (error) {
                console.error('Error saving message:', error)
                return { data: null, error }
            }

            // Update session's updated_at
            await supabase
                .from('chat_sessions')
                .update({ updated_at: new Date().toISOString() })
                .eq('id', targetSessionId)

            return { data, error: null }
        } catch (err) {
            console.error('Save message exception:', err)
            return { data: null, error: err }
        } finally {
            savingMessage.value = false
        }
    }

    // Load messages for a specific session
    async function loadMessages(sessionId) {
        try {
            const { data, error } = await supabase
                .from('chat_messages')
                .select('*')
                .eq('session_id', sessionId)
                .order('created_at', { ascending: true })

            if (error) {
                console.error('Error loading messages:', error)
                return { data: null, error }
            }

            return { data, error: null }
        } catch (err) {
            console.error('Load messages exception:', err)
            return { data: null, error: err }
        }
    }

    // Switch to a different session and load its messages
    async function switchSession(sessionId) {
        currentSessionId.value = sessionId
        const { data: messages } = await loadMessages(sessionId)
        return messages || []
    }

    // Update session title
    async function updateSessionTitle(sessionId, newTitle) {
        try {
            const { data, error } = await supabase
                .from('chat_sessions')
                .update({ title: newTitle })
                .eq('id', sessionId)
                .select()
                .single()

            if (error) {
                console.error('Error updating session title:', error)
                return { data: null, error }
            }

            // Update local state
            const session = sessions.value.find(s => s.id === sessionId)
            if (session) {
                session.title = newTitle
            }

            return { data, error: null }
        } catch (err) {
            console.error('Update session title exception:', err)
            return { data: null, error: err }
        }
    }

    // Delete a session
    async function deleteSession(sessionId) {
        try {
            const { error } = await supabase
                .from('chat_sessions')
                .delete()
                .eq('id', sessionId)

            if (error) {
                console.error('Error deleting session:', error)
                return { error }
            }

            // Remove from local state
            sessions.value = sessions.value.filter(s => s.id !== sessionId)

            if (currentSessionId.value === sessionId) {
                currentSessionId.value = null
            }

            return { error: null }
        } catch (err) {
            console.error('Delete session exception:', err)
            return { error: err }
        }
    }

    // Clear current session (for new chat)
    function clearCurrentSession() {
        currentSessionId.value = null
    }

    return {
        // State
        sessions,
        sortedSessions,
        currentSessionId,
        currentSession,
        loadingSessions,
        savingMessage,

        // Methods
        loadSessions,
        createSession,
        saveMessage,
        loadMessages,
        switchSession,
        updateSessionTitle,
        deleteSession,
        clearCurrentSession
    }
}

export default useChatHistory
