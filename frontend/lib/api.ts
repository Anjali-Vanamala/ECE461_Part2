// API configuration
// Default to the deployed API Gateway URL
const API_BASE_URL = 'https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod'

// Export API base URL for use in components
export { API_BASE_URL }

// API client functions
export async function fetchModels() {
  // Use regex endpoint with .* to get all artifacts (models)
  try {
    const response = await fetch(`${API_BASE_URL}/artifact/byRegEx`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ regex: '.*' }), // Match all artifacts
    })
    
    if (!response.ok) {
      // 404 means no artifacts found - return empty array instead of error
      if (response.status === 404) {
        return []
      }
      
      const errorText = response.statusText || `HTTP ${response.status}`
      let errorDetail = errorText
      try {
        const errorData = await response.json()
        errorDetail = errorData.detail || errorData.message || errorText
      } catch {
        // If response body isn't JSON, use status text
      }
      throw new Error(`Failed to fetch models: ${errorDetail}`)
    }
    
    return response.json()
  } catch (error) {
    // Handle network errors (CORS, connection refused, etc.)
    if (error instanceof TypeError) {
      throw new Error(`Network error: Unable to connect to API. Please check if the API is running at ${API_BASE_URL}`)
    }
    throw error
  }
}

export async function fetchModelById(id: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/artifacts/model/${id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Model not found')
      }
      const errorText = response.statusText || `HTTP ${response.status}`
      let errorDetail = errorText
      try {
        const errorData = await response.json()
        errorDetail = errorData.detail || errorData.message || errorText
      } catch {
        // If response body isn't JSON, use status text
      }
      throw new Error(`Failed to fetch model: ${errorDetail}`)
    }
    
    return response.json()
  } catch (error) {
    // Handle network errors
    if (error instanceof TypeError) {
      throw new Error(`Network error: Unable to connect to API. Please check if the API is running at ${API_BASE_URL}`)
    }
    throw error
  }
}

export async function fetchModelRating(id: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/artifact/model/${id}/rate`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      if (response.status === 404) {
        return null // Rating might not exist
      }
      const errorText = response.statusText || `HTTP ${response.status}`
      let errorDetail = errorText
      try {
        const errorData = await response.json()
        errorDetail = errorData.detail || errorData.message || errorText
      } catch {
        // If response body isn't JSON, use status text
      }
      throw new Error(`Failed to fetch rating: ${errorDetail}`)
    }
    
    return response.json()
  } catch (error) {
    // Handle network errors - for ratings, we return null if it's a network error
    // since ratings are optional
    if (error instanceof TypeError) {
      console.warn(`Network error fetching rating for ${id}:`, error.message)
      return null
    }
    throw error
  }
}

export async function ingestModel(url: string, name?: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/artifact/model`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url,
        name: name || undefined,
      }),
    })
    
    if (!response.ok) {
      const errorText = response.statusText || `HTTP ${response.status}`
      let errorDetail = errorText
      try {
        const errorData = await response.json()
        errorDetail = errorData.detail || errorData.message || errorText
      } catch {
        // If response body isn't JSON, use status text
      }
      throw new Error(errorDetail || `Failed to ingest model: ${errorText}`)
    }
    
    return response.json()
  } catch (error) {
    // Handle network errors
    if (error instanceof TypeError) {
      throw new Error(`Network error: Unable to connect to API. Please check if the API is running at ${API_BASE_URL}`)
    }
    throw error
  }
}

export async function fetchHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      const errorText = response.statusText || `HTTP ${response.status}`
      throw new Error(`Failed to fetch health: ${errorText}`)
    }
    
    return response.json()
  } catch (error) {
    // Handle network errors
    if (error instanceof TypeError) {
      throw new Error(`Network error: Unable to connect to API. Please check if the API is running at ${API_BASE_URL}`)
    }
    throw error
  }
}

export async function fetchHealthComponents(windowMinutes: number = 60, includeTimeline: boolean = false) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/health/components?window_minutes=${windowMinutes}&include_timeline=${includeTimeline}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )
    
    if (!response.ok) {
      const errorText = response.statusText || `HTTP ${response.status}`
      let errorDetail = errorText
      try {
        const errorData = await response.json()
        errorDetail = errorData.detail || errorData.message || errorText
      } catch {
        // If response body isn't JSON, use status text
      }
      throw new Error(`Failed to fetch health components: ${errorDetail}`)
    }
    
    return response.json()
  } catch (error) {
    // Handle network errors
    if (error instanceof TypeError) {
      throw new Error(`Network error: Unable to connect to API. Please check if the API is running at ${API_BASE_URL}`)
    }
    throw error
  }
}


