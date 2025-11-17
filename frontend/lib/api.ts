// API configuration
// Default to the deployed API Gateway URL
export const API_BASE_URL = 'https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod'

// API client functions
export async function fetchModels() {
  // Use regex endpoint with .* to get all artifacts (models)
  const response = await fetch(`${API_BASE_URL}/artifact/byRegEx`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ regex: '.*' }), // Match all artifacts
  })
  
  if (!response.ok) {
    throw new Error(`Failed to fetch models: ${response.statusText}`)
  }
  
  return response.json()
}

export async function fetchModelById(id: string) {
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
    throw new Error(`Failed to fetch model: ${response.statusText}`)
  }
  
  return response.json()
}

export async function fetchModelRating(id: string) {
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
    throw new Error(`Failed to fetch rating: ${response.statusText}`)
  }
  
  return response.json()
}

export async function ingestModel(url: string, name?: string) {
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
    const errorData = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(errorData.detail || `Failed to ingest model: ${response.statusText}`)
  }
  
  return response.json()
}

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  
  if (!response.ok) {
    throw new Error(`Failed to fetch health: ${response.statusText}`)
  }
  
  return response.json()
}

export async function fetchHealthComponents(windowMinutes: number = 60, includeTimeline: boolean = false) {
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
    throw new Error(`Failed to fetch health components: ${response.statusText}`)
  }
  
  return response.json()
}

// Export API base URL for use in components
export { API_BASE_URL }

