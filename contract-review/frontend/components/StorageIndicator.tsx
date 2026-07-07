'use client'

import { useState, useEffect, memo } from 'react'
import { API_BASE_URL } from '@/lib/config'
import { authenticatedFetch } from '@/lib/api'
import { logger } from '@/lib/logger'

interface StorageData {
  user_id?: string
  storage_quota: number
  storage_used: number
  storage_available: number
  usage_percentage: number
}

interface StorageIndicatorProps {
  apiBaseUrl?: string
  onStorageUpdate?: (data: StorageData) => void
  refreshTrigger?: number
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${Math.round(bytes / Math.pow(k, i))} ${sizes[i]}`
}

function StorageIndicator({
  apiBaseUrl = API_BASE_URL,
  onStorageUpdate,
  refreshTrigger
}: StorageIndicatorProps) {
  const [storageData, setStorageData] = useState<StorageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStorageData()
  }, [refreshTrigger])

  async function fetchStorageData() {
    try {
      setLoading(true)
      setError(null)

      const response = await authenticatedFetch(`${apiBaseUrl}/api/users/me/storage`)

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          setError('Not authenticated')
        } else {
          throw new Error('Failed to fetch storage data')
        }
        return
      }

      const data: StorageData = await response.json()
      setStorageData(data)

      if (onStorageUpdate) {
        onStorageUpdate(data)
      }
    } catch (err) {
      if (error !== 'Not authenticated') {
        logger.error('Error fetching storage data:', err)
      }
      setError('Unable to load storage information')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg shadow-sm px-3 py-2">
        <div className="animate-pulse flex items-center space-x-2">
          <div className="h-2 bg-gray-200 rounded flex-1"></div>
          <div className="h-4 w-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error || !storageData) {
    return null
  }

  const { usage_percentage, storage_used, storage_quota } = storageData

  const storage_used_formatted = formatBytes(storage_used)
  const storage_quota_formatted = formatBytes(storage_quota)

  const displayPercentage = storage_used > 0
    ? Math.max(usage_percentage, 2)
    : 0

  const getProgressColor = () => {
    if (usage_percentage >= 90) return 'bg-red-500'
    if (usage_percentage >= 75) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const getBackgroundColor = () => {
    if (usage_percentage >= 90) return 'bg-red-50'
    if (usage_percentage >= 75) return 'bg-yellow-50'
    return 'bg-[#F2FFF4]'
  }

  const getTextColor = () => {
    if (usage_percentage >= 90) return 'text-red-700'
    if (usage_percentage >= 75) return 'text-yellow-700'
    return 'text-green-700'
  }

  return (
    <div className={`${getBackgroundColor()} border border-gray-200 rounded-lg shadow-sm transition-colors duration-300 px-3 py-2`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className={`text-xs font-medium ${getTextColor()}`}>
          Storage: {storage_used_formatted} / {storage_quota_formatted}
        </span>
        <span className={`text-xs font-semibold ${getTextColor()}`}>
          {usage_percentage.toFixed(1)}%
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`${getProgressColor()} h-full rounded-full transition-all duration-500 ease-out`}
          style={{ width: `${Math.min(displayPercentage, 100)}%` }}
        ></div>
      </div>
    </div>
  )
}

export default memo(StorageIndicator);
export { type StorageData }
