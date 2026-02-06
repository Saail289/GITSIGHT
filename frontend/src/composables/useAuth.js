/**
 * Authentication Composable
 * Provides reactive auth state and methods for Google OAuth
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { supabase } from '../supabase'

// Shared reactive state
const user = ref(null)
const loading = ref(true)
const error = ref(null)

// Auth state subscription
let authSubscription = null

export function useAuth() {
    const isAuthenticated = computed(() => !!user.value)

    const userDisplayName = computed(() => {
        if (!user.value) return null
        return user.value.user_metadata?.full_name ||
            user.value.user_metadata?.name ||
            user.value.email?.split('@')[0] ||
            'User'
    })

    const userAvatar = computed(() => {
        if (!user.value) return null
        return user.value.user_metadata?.avatar_url ||
            user.value.user_metadata?.picture ||
            null
    })

    const userEmail = computed(() => {
        return user.value?.email || null
    })

    // Initialize auth state
    async function initAuth() {
        try {
            loading.value = true

            // Get current session
            const { data: { session }, error: sessionError } = await supabase.auth.getSession()

            if (sessionError) {
                console.error('Error getting session:', sessionError)
                error.value = sessionError.message
            } else {
                user.value = session?.user || null
            }

            // Subscribe to auth changes
            const { data: { subscription } } = supabase.auth.onAuthStateChange(
                (event, session) => {
                    console.log('Auth state changed:', event)
                    user.value = session?.user || null

                    if (event === 'SIGNED_OUT') {
                        // Clear any cached data
                        error.value = null
                    }
                }
            )

            authSubscription = subscription
        } catch (err) {
            console.error('Auth initialization error:', err)
            error.value = err.message
        } finally {
            loading.value = false
        }
    }

    // Sign in with Google
    async function signInWithGoogle() {
        try {
            loading.value = true
            error.value = null

            const { data, error: signInError } = await supabase.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: window.location.origin
                }
            })

            if (signInError) {
                error.value = signInError.message
                console.error('Sign in error:', signInError)
            }

            return { data, error: signInError }
        } catch (err) {
            error.value = err.message
            console.error('Sign in exception:', err)
            return { data: null, error: err }
        } finally {
            loading.value = false
        }
    }

    // Sign out
    async function signOut() {
        try {
            loading.value = true
            error.value = null

            const { error: signOutError } = await supabase.auth.signOut()

            if (signOutError) {
                error.value = signOutError.message
                console.error('Sign out error:', signOutError)
            } else {
                user.value = null
            }

            return { error: signOutError }
        } catch (err) {
            error.value = err.message
            console.error('Sign out exception:', err)
            return { error: err }
        } finally {
            loading.value = false
        }
    }

    // Cleanup subscription on unmount
    function cleanup() {
        if (authSubscription) {
            authSubscription.unsubscribe()
            authSubscription = null
        }
    }

    // Auto-initialize when composable is used
    onMounted(() => {
        if (!authSubscription) {
            initAuth()
        }
    })

    onUnmounted(() => {
        // Don't cleanup here as other components might still use it
        // cleanup()
    })

    return {
        // State
        user,
        loading,
        error,
        isAuthenticated,
        userDisplayName,
        userAvatar,
        userEmail,

        // Methods
        initAuth,
        signInWithGoogle,
        signOut,
        cleanup
    }
}

export default useAuth
