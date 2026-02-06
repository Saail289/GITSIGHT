/**
 * API service for communicating with the backend
 * Handles all HTTP requests to FastAPI server
 */

import axios from 'axios'

// Get API URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes timeout for ingestion
})

/**
 * API endpoints
 */
export const api = {
  /**
   * Check if API is healthy
   */
  async healthCheck() {
    try {
      const response = await apiClient.get('/api/health')
      return { success: true, data: response.data }
    } catch (error) {
      return { success: false, error: error.message }
    }
  },

  /**
   * Get available models
   */
  async getModels() {
    try {
      const response = await apiClient.get('/api/models')
      return { success: true, data: response.data }
    } catch (error) {
      return { success: false, error: error.message }
    }
  },

  /**
   * Ingest a GitHub repository
   * @param {string} repoUrl - GitHub repository URL
   * @param {string} userId - Optional user ID
   */
  async ingestRepository(repoUrl, userId = 'default') {
    try {
      const response = await apiClient.post('/api/ingest', {
        repo_url: repoUrl,
        user_id: userId,
      })
      return { success: true, data: response.data }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message
      return { success: false, error: errorMessage }
    }
  },

  /**
   * Query a repository with a question
   * @param {string} repoUrl - GitHub repository URL
   * @param {string} question - User's question
   * @param {string} modelPreference - LLM model: 'high_reasoning' or 'fast'
   */
  async queryRepository(repoUrl, question, modelPreference = 'high_reasoning') {
    try {
      const response = await apiClient.post('/api/query', {
        repo_url: repoUrl,
        question: question,
        llm_model: modelPreference,
      })
      return { success: true, data: response.data }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message
      return { success: false, error: errorMessage }
    }
  },

  /**
   * Delete a repository's data
   * @param {string} repoUrl - GitHub repository URL
   */
  async deleteRepository(repoUrl) {
    try {
      const response = await apiClient.delete('/api/repository', {
        params: { repo_url: repoUrl },
      })
      return { success: true, data: response.data }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message
      return { success: false, error: errorMessage }
    }
  },
}

export default api