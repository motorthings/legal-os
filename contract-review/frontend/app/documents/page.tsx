'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useSearchParams, useRouter } from 'next/navigation'
import Image from 'next/image'
import DocumentUpload from '@/components/DocumentUpload'
import LoadingSpinner from '@/components/LoadingSpinner'
import ConfirmModal from '@/components/ConfirmModal'
import StorageIndicator from '@/components/StorageIndicator'
import Link from 'next/link'
import { logger } from '@/lib/logger'
import {
  getGoogleDriveStatus,
  connectGoogleDrive,
  syncGoogleDrive,
  syncGoogleDriveFiles,
  listFolderFiles,
  disconnectGoogleDrive,
  formatLastSync,
  type GoogleDriveStatus,
  type GoogleDriveFile
} from '@/lib/googleDrive'
import {
  getNotionStatus,
  connectNotion,
  syncNotion,
  disconnectNotion,
  getNotionPages,
  type NotionStatus,
  type NotionPage
} from '@/lib/notion'
import { apiGet, apiPatch, apiPost, apiDelete } from '@/lib/api'
import { API_BASE_URL } from '@/lib/config'

interface Document {
  id: string
  filename: string
  uploaded_at: string
  processed: boolean
  processing_status?: string
  processing_error?: string
  storage_url: string
  source_platform?: string
  external_url?: string
  google_drive_file_id?: string
  notion_page_id?: string
  sync_cadence?: string
  file_size?: number
  is_core_document?: boolean
}

function DocumentsContent() {
  const { user, profile, signOut } = useAuth()
  const searchParams = useSearchParams()
  const router = useRouter()

  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Google Drive state
  const [driveStatus, setDriveStatus] = useState<GoogleDriveStatus | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [syncSuccess, setSyncSuccess] = useState<string | null>(null)
  const [syncFrequency, setSyncFrequency] = useState<string>('manual')
  const [nextSyncScheduled, setNextSyncScheduled] = useState<string | null>(null)
  const [driveExpanded, setDriveExpanded] = useState<boolean>(false)
  const [showDisconnectModal, setShowDisconnectModal] = useState(false)
  const [selectedFolderId, setSelectedFolderId] = useState<string>('')
  const [selectedFolderName, setSelectedFolderName] = useState<string>('')
  const [driveFiles, setDriveFiles] = useState<GoogleDriveFile[]>([])
  const [driveFilesLoading, setDriveFilesLoading] = useState(false)
  const [selectedDriveFileIds, setSelectedDriveFileIds] = useState<Set<string>>(new Set())
  const [isFileUrl, setIsFileUrl] = useState<boolean>(false)

  // Notion state
  const [notionStatus, setNotionStatus] = useState<NotionStatus | null>(null)
  const [notionSyncing, setNotionSyncing] = useState(false)
  const [notionSyncError, setNotionSyncError] = useState<string | null>(null)
  const [notionSyncSuccess, setNotionSyncSuccess] = useState<string | null>(null)
  const [notionExpanded, setNotionExpanded] = useState<boolean>(false)
  const [showNotionDisconnectModal, setShowNotionDisconnectModal] = useState(false)
  const [notionPageIds, setNotionPageIds] = useState<string>('')
  const [notionSyncFrequency, setNotionSyncFrequency] = useState<string>('manual')
  const [notionNextSyncScheduled, setNotionNextSyncScheduled] = useState<string | null>(null)
  const [notionPages, setNotionPages] = useState<NotionPage[]>([])
  const [notionPagesLoading, setNotionPagesLoading] = useState(false)
  const [selectedNotionPageIds, setSelectedNotionPageIds] = useState<Set<string>>(new Set())

  // Document actions state
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null)
  const [syncingDocId, setSyncingDocId] = useState<string | null>(null)
  const [showInfoModal, setShowInfoModal] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [docToDelete, setDocToDelete] = useState<Document | null>(null)
  const [docSyncCadence, setDocSyncCadence] = useState<string>('manual')
  const [tempSyncCadence, setTempSyncCadence] = useState<string>('manual')

  // General document notifications (separate from Drive/Notion specific ones)
  const [generalSuccess, setGeneralSuccess] = useState<string | null>(null)
  const [generalError, setGeneralError] = useState<string | null>(null)

  // Storage refresh trigger
  const [storageRefreshTrigger, setStorageRefreshTrigger] = useState<number>(0)

  // Upload and Documents section state
  const [uploadExpanded, setUploadExpanded] = useState<boolean>(false)
  const [documentsExpanded, setDocumentsExpanded] = useState<boolean>(false)
  const [coreDocumentsExpanded, setCoreDocumentsExpanded] = useState<boolean>(false)

  // Hamburger menu state
  const [menuOpen, setMenuOpen] = useState(false)

  // User menu helpers
  const isAdmin = profile?.role === 'admin'
  const getInitials = (name?: string | null) => {
    if (!name) return '?'
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  const handleSignOut = async () => {
    await signOut()
    router.push('/auth/login')
  }

  // Define functions first with useCallback
  const loadDocuments = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true)
      }
      // Use new user-based endpoint - users only see their own documents
      const data = await apiGet<{ documents: Document[] }>(`/api/users/me/documents`)
      setDocuments(data.documents || [])
      setError(null)
    } catch (err) {
      logger.error('Error loading documents:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }, [])

  const handleDocumentsChange = useCallback(async () => {
    await loadDocuments()
    setStorageRefreshTrigger(prev => prev + 1)  // Refresh storage indicator
  }, [loadDocuments])

  const loadSyncSettings = useCallback(async () => {
    try {
      const data = await apiGet<{ sync_frequency: string; next_sync_scheduled: any }>('/api/google-drive/sync-settings')
      setSyncFrequency(data.sync_frequency || 'manual')
      setNextSyncScheduled(data.next_sync_scheduled)
    } catch (err) {
      logger.error('Error loading sync settings:', err)
    }
  }, [])

  const checkDriveStatus = useCallback(async () => {
    try {
      const status = await getGoogleDriveStatus()
      setDriveStatus(status)

      // Load sync settings if connected
      if (status.connected) {
        loadSyncSettings()
      }
    } catch (err) {
      logger.error('Error checking Drive status:', err)
    }
  }, [loadSyncSettings])

  // Notion status check function (not memoized to avoid TypeScript confusion)
  async function checkNotionStatusFn() {
    try {
      const status = await getNotionStatus()
      setNotionStatus(status)
    } catch (err) {
      logger.error('Error checking Notion status:', err)
    }
  }

  // Now use the functions in useEffect hooks
  useEffect(() => {
    loadDocuments()
    checkDriveStatus()
    checkNotionStatusFn()
     
    // Intentionally run only on mount - including function dependencies would cause infinite re-fetch loops
  }, [])

  // Auto-refresh when there are unprocessed documents
  useEffect(() => {
    const hasUnprocessedDocs = documents.some(doc => !doc.processed)

    if (hasUnprocessedDocs) {
      // Poll every 2 seconds to check for processing completion
      // Use showLoading=false to avoid UI flashing during background polling
      const intervalId = setInterval(() => {
        loadDocuments(false)
      }, 2000)

      return () => clearInterval(intervalId)
    }
  }, [documents, loadDocuments])

  // Listen for messages from OAuth popup
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Verify origin for security
      if (event.origin !== window.location.origin) return

      if (event.data.type === 'google_drive_connected') {
        setSyncSuccess('Google Drive connected successfully!')
        checkDriveStatus()
        loadDocuments()
      } else if (event.data.type === 'google_drive_error') {
        setSyncError(event.data.message || 'Failed to connect Google Drive')
      } else if (event.data.type === 'notion_connected') {
        setNotionSyncSuccess('Notion connected successfully!')
        checkNotionStatusFn()
        loadDocuments()
        loadNotionPages()
      } else if (event.data.type === 'notion_error') {
        setNotionSyncError(event.data.message || 'Failed to connect Notion')
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
     
    // Event listener setup - only needs to run once on mount, handler uses current state via closures
  }, [])

  // Listen for Notion OAuth completion (for when popup loses window.opener)
  useEffect(() => {
    const handleNotionOAuthComplete = () => {
      // Wait a moment for the backend to process
      setTimeout(async () => {
        try {
          const status = await getNotionStatus()

          if (status.connected) {
            setNotionSyncSuccess('Notion connected successfully!')
            setNotionStatus(status)  // IMPORTANT: Update the state
            loadDocuments()
            loadNotionPages()
          } else {
            logger.warn('⚠️ Notion not connected yet, retrying in 2 seconds...')
            // Try again after a longer delay
            setTimeout(async () => {
              const retryStatus = await getNotionStatus()

              if (retryStatus.connected) {
                setNotionSyncSuccess('Notion connected successfully!')
                setNotionStatus(retryStatus)  // IMPORTANT: Update the state
                loadDocuments()
                loadNotionPages()
              } else {
                logger.error('❌ Notion still not connected after retry')
                setNotionSyncError('Connection succeeded but unable to detect status. Please refresh the page.')
              }
            }, 2000)
          }
        } catch (err) {
          logger.error('❌ Error checking Notion status after OAuth:', err)
          setNotionSyncError('Failed to verify connection. Please refresh the page.')
        }
      }, 1000)
    }

    window.addEventListener('notion-oauth-complete', handleNotionOAuthComplete)
    return () => window.removeEventListener('notion-oauth-complete', handleNotionOAuthComplete)
     
    // Custom event listener setup - only needs to run once on mount
  }, [])

  // Load Notion pages when connected and expanded
  useEffect(() => {
    if (notionStatus?.connected && notionExpanded && notionPages.length === 0) {
      loadNotionPages()
    }
     
    // Only depend on connection status and expanded state - loadNotionPages is stable and notionPages is checked inline
  }, [notionStatus?.connected, notionExpanded])

  // Check for OAuth callback
  useEffect(() => {
    const driveParam = searchParams?.get('google_drive')
    if (driveParam === 'connected') {
      // Check if this is a popup window (opened by window.open)
      if (window.opener) {
        // This is a popup - close it and notify parent
        try {
          window.opener.postMessage({ type: 'google_drive_connected' }, window.location.origin)
          window.close()
        } catch (e) {
          logger.error('Failed to close popup:', e)
        }
      } else {
        // This is the main window - show success message
        setSyncSuccess('Google Drive connected successfully!')
        checkDriveStatus()
        // Clear URL parameter
        window.history.replaceState({}, '', '/documents')
      }
    } else if (driveParam === 'error') {
      const message = searchParams?.get('message') || 'Failed to connect Google Drive'

      // Check if this is a popup window
      if (window.opener) {
        // Notify parent and close
        try {
          window.opener.postMessage({
            type: 'google_drive_error',
            message
          }, window.location.origin)
          window.close()
        } catch (e) {
          logger.error('Failed to close popup:', e)
        }
      } else {
        // Show error in main window
        setSyncError(message)
        window.history.replaceState({}, '', '/documents')
      }
    }

    // Check for Notion OAuth callback
    const notionParam = searchParams?.get('notion')
    if (notionParam === 'connected') {
      if (window.opener) {
        try {
          window.opener.postMessage({ type: 'notion_connected' }, window.location.origin)
          // Give parent time to receive message, then close
          setTimeout(() => window.close(), 100)
        } catch (e) {
          logger.error('Failed to communicate with parent window:', e)
          // Close anyway - parent will detect closure and check status
          window.close()
        }
      } else {
        // This is the main window (not a popup)
        setNotionSyncSuccess('Notion connected successfully!')
        checkNotionStatusFn()
        loadNotionPages()
        window.history.replaceState({}, '', '/documents')
      }
    } else if (notionParam === 'error') {
      const message = searchParams?.get('message') || 'Failed to connect Notion'
      if (window.opener) {
        try {
          window.opener.postMessage({
            type: 'notion_error',
            message
          }, window.location.origin)
          setTimeout(() => window.close(), 100)
        } catch (e) {
          logger.error('Failed to communicate with parent window:', e)
          window.close()
        }
      } else{
        setNotionSyncError(message)
        window.history.replaceState({}, '', '/documents')
      }
    }
     
    // OAuth redirect check - only needs to run once on mount to check URL params, uses searchParams from props
  }, [])

  function formatDate(isoString: string) {
    const date = new Date(isoString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  function formatFileSize(bytes?: number): string {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  async function handleSyncFrequencyChange(newFrequency: string) {
    try {
      setSyncError(null)

      const data = await apiPatch<{ sync_frequency: string; next_sync_scheduled: any }>('/api/google-drive/sync-settings', {
        sync_frequency: newFrequency,
        default_folder_id: driveStatus?.folder_id,
        default_folder_name: driveStatus?.folder_name
      })

      setSyncFrequency(data.sync_frequency)
      setNextSyncScheduled(data.next_sync_scheduled)
      setSyncSuccess('Sync settings updated successfully')
      setTimeout(() => setSyncSuccess(null), 3000)
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Failed to update settings')
    }
  }

  async function handleConnectDrive() {
    try {
      setSyncError(null)
      await connectGoogleDrive()
      // The OAuth flow will redirect back to this page
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Failed to connect Google Drive')
    }
  }

  async function handleSync() {
    // Check if folder ID is empty - require it
    if (!selectedFolderId || selectedFolderId.trim() === '') {
      setSyncError('Please enter a Google Drive folder ID')
      return
    }

    // Proceed with sync
    await performSync()
  }

  async function performSync() {
    try {
      setSyncing(true)
      setSyncError(null)
      setSyncSuccess(null)

      // Pass folder ID and name (required)
      const result = await syncGoogleDrive(
        selectedFolderId,
        selectedFolderName || null
      )

      // Sync now returns immediately with status "started"
      setSyncSuccess(
        'Sync started! Documents are being downloaded and will appear below with a "Processing" tag. The tag will disappear when each document is ready.'
      )

      // Immediately refresh document list to show any quick syncs
      loadDocuments()

      // Auto-hide success message after 10 seconds
      setTimeout(() => setSyncSuccess(null), 10000)
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  async function loadDriveFiles() {
    if (!selectedFolderId) return

    try {
      setDriveFilesLoading(true)
      setSyncError(null)
      const files = await listFolderFiles(selectedFolderId)
      setDriveFiles(files)
    } catch (err) {
      logger.error('Failed to load Google Drive files:', err)
      setSyncError(err instanceof Error ? err.message : 'Failed to load files')
      setDriveFiles([])
    } finally {
      setDriveFilesLoading(false)
    }
  }

  async function handleDriveFilesSync() {
    if (selectedDriveFileIds.size === 0) {
      setSyncError('Please select at least one file to sync')
      return
    }

    try {
      setSyncing(true)
      setSyncError(null)
      setSyncSuccess(null)

      const fileIdArray = Array.from(selectedDriveFileIds)

      await syncGoogleDriveFiles(fileIdArray)

      setSyncSuccess('File/folder sync started - Check the Documents section below for details')

      // Immediately refresh document list to show placeholder documents
      await loadDocuments(false)

      // Clear selection
      setSelectedDriveFileIds(new Set())

      setTimeout(() => setSyncSuccess(null), 10000)
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  async function handleSyncSingleFile(fileId: string) {
    try {
      setSyncing(true)
      setSyncError(null)
      setSyncSuccess(null)

      await syncGoogleDriveFiles([fileId])

      setSyncSuccess('File/folder sync started - Check the Documents section below for details')

      // Immediately refresh document list to show placeholder document
      await loadDocuments(false)

      // Clear the input field and reset file flag
      setSelectedFolderId('')
      setIsFileUrl(false)

      setTimeout(() => setSyncSuccess(null), 10000)
    } catch (err) {
      logger.error('Error syncing file:', err)
      setSyncError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  function toggleDriveFileSelection(fileId: string) {
    setSelectedDriveFileIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(fileId)) {
        newSet.delete(fileId)
      } else {
        newSet.add(fileId)
      }
      return newSet
    })
  }

  function selectAllDriveFiles() {
    setSelectedDriveFileIds(new Set(driveFiles.map(f => f.id)))
  }

  function deselectAllDriveFiles() {
    setSelectedDriveFileIds(new Set())
  }

  function handleDisconnectClick() {
    setShowDisconnectModal(true)
  }

  async function handleDisconnectConfirm() {
    setShowDisconnectModal(false)

    try {
      setSyncError(null)
      await disconnectGoogleDrive()
      setSyncSuccess('Google Drive disconnected')
      await checkDriveStatus()

      setTimeout(() => setSyncSuccess(null), 3000)
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Failed to disconnect')
    }
  }

  // Notion handler functions
  async function handleConnectNotion() {
    try {
      setNotionSyncError(null)
      await connectNotion()
      // The OAuth flow will redirect back to this page
    } catch (err) {
      setNotionSyncError(err instanceof Error ? err.message : 'Failed to connect Notion')
    }
  }

  async function handleNotionSync() {
    if (selectedNotionPageIds.size === 0) {
      setNotionSyncError('Please select at least one page to sync')
      return
    }

    try {
      setNotionSyncing(true)
      setNotionSyncError(null)
      setNotionSyncSuccess(null)

      const pageIdArray = Array.from(selectedNotionPageIds)

      await syncNotion(pageIdArray)

      setNotionSyncSuccess(
        `Sync started for ${pageIdArray.length} page(s)! Pages are being downloaded and will appear below with a "Processing" tag. The tag will disappear when each page is ready.`
      )

      // Wait a moment for background task to create initial records, then refresh
      setTimeout(async () => {
        await loadDocuments(false)
      }, 1500)

      setTimeout(() => setNotionSyncSuccess(null), 10000)
    } catch (err) {
      setNotionSyncError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setNotionSyncing(false)
    }
  }

  async function loadNotionPages() {
    try {
      setNotionPagesLoading(true)
      const response = await getNotionPages()
      setNotionPages(response.pages)
    } catch (err) {
      logger.error('Failed to load Notion pages:', err)
      setNotionSyncError(err instanceof Error ? err.message : 'Failed to load pages')
    } finally {
      setNotionPagesLoading(false)
    }
  }

  function toggleNotionPageSelection(pageId: string) {
    setSelectedNotionPageIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(pageId)) {
        newSet.delete(pageId)
      } else {
        newSet.add(pageId)
      }
      return newSet
    })
  }

  function selectAllNotionPages() {
    setSelectedNotionPageIds(new Set(notionPages.map(p => p.id)))
  }

  function deselectAllNotionPages() {
    setSelectedNotionPageIds(new Set())
  }

  function handleNotionDisconnectClick() {
    setShowNotionDisconnectModal(true)
  }

  async function handleNotionDisconnectConfirm() {
    setShowNotionDisconnectModal(false)

    try {
      setNotionSyncError(null)
      await disconnectNotion()
      setNotionSyncSuccess('Notion disconnected')
      await checkNotionStatusFn()

      setTimeout(() => setNotionSyncSuccess(null), 3000)
    } catch (err) {
      setNotionSyncError(err instanceof Error ? err.message : 'Failed to disconnect')
    }
  }

  async function handleNotionSyncFrequencyChange(newFrequency: string) {
    try {
      setNotionSyncError(null)

      const data = await apiPatch<{ sync_frequency: string; next_sync_scheduled: any }>('/api/notion/sync-settings', {
        sync_frequency: newFrequency
      })

      setNotionSyncFrequency(data.sync_frequency)
      setNotionNextSyncScheduled(data.next_sync_scheduled)
      setNotionSyncSuccess('Sync settings updated successfully')
      setTimeout(() => setNotionSyncSuccess(null), 3000)
    } catch (err) {
      setNotionSyncError(err instanceof Error ? err.message : 'Failed to update settings')
    }
  }

  // Document action handlers
  function handleDocumentInfo(doc: Document) {
    setSelectedDoc(doc)
    // Load actual sync cadence from document, default to 'manual'
    const currentCadence = doc.sync_cadence || 'manual'
    setDocSyncCadence(currentCadence)
    setTempSyncCadence(currentCadence)
    setShowInfoModal(true)
  }

  async function handleSaveDocumentInfo() {
    if (!selectedDoc) return

    try {
      // Only save if cadence changed
      if (tempSyncCadence !== docSyncCadence) {
        // Save to backend
        await apiPatch(`/api/documents/${selectedDoc.id}/sync-cadence`, {
          sync_cadence: tempSyncCadence
        })

        // Update local state
        setDocSyncCadence(tempSyncCadence)

        // Update the document in the documents list
        setDocuments(prevDocs =>
          prevDocs.map(doc =>
            doc.id === selectedDoc.id
              ? { ...doc, sync_cadence: tempSyncCadence }
              : doc
          )
        )

        setGeneralSuccess(`Sync cadence updated to ${tempSyncCadence}`)
        setTimeout(() => setGeneralSuccess(null), 3000)
      }

      // Close modal
      setShowInfoModal(false)
    } catch (err) {
      setGeneralError(err instanceof Error ? err.message : 'Failed to update sync cadence')
      setTimeout(() => setGeneralError(null), 3000)
    }
  }

  function handleDeleteClick(doc: Document) {
    setDocToDelete(doc)
    setShowDeleteModal(true)
  }

  async function handleDeleteConfirm() {
    if (!docToDelete) return

    setShowDeleteModal(false)
    setDeletingDocId(docToDelete.id)

    try {
      await apiDelete(`/api/documents/${docToDelete.id}`)
      setGeneralSuccess(`Deleted ${docToDelete.filename}`)
      await loadDocuments()
      setStorageRefreshTrigger(prev => prev + 1)  // Refresh storage indicator
      setTimeout(() => setGeneralSuccess(null), 3000)
    } catch (err) {
      setGeneralError(err instanceof Error ? err.message : 'Failed to delete document')
      setTimeout(() => setGeneralError(null), 3000)
    } finally {
      setDeletingDocId(null)
      setDocToDelete(null)
    }
  }

  async function handleDocumentSync(doc: Document) {
    if (!doc.google_drive_file_id) {
      setSyncError('Only Google Drive documents can be synced')
      setTimeout(() => setSyncError(null), 3000)
      return
    }

    setSyncingDocId(doc.id)

    try {
      // Trigger re-sync of the specific document
      await apiPost(`/api/google-drive/sync-document/${doc.google_drive_file_id}`)
      setSyncSuccess(`Syncing ${doc.filename}...`)
      setTimeout(() => {
        setSyncSuccess(null)
        handleDocumentsChange()
      }, 2000)
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Failed to sync document')
    } finally {
      setSyncingDocId(null)
    }
  }

  return (
    <div className="min-h-screen bg-page">
      {/* Header */}
      <div className="bg-card border-b border-default shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between relative">
            {/* Hamburger Menu and Profile Avatar */}
            <div className="relative flex items-center gap-3">
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="p-2 hover:bg-hover rounded-md transition-colors"
                aria-label="Menu"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>

              {/* Profile Avatar (display only) */}
              {profile?.avatar_url ? (
                <Image
                  src={profile.avatar_url}
                  alt={profile?.name || 'User'}
                  width={36}
                  height={36}
                  className="w-9 h-9 rounded-full object-cover"
                />
              ) : (
                <div className="w-9 h-9 rounded-full bg-brand flex items-center justify-center">
                  <span className="text-white text-sm font-semibold">
                    {getInitials(profile?.name)}
                  </span>
                </div>
              )}

              {/* Dropdown Menu */}
              {menuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setMenuOpen(false)}
                  />
                  <div className="absolute left-0 top-full mt-2 w-64 bg-card border border-default rounded-lg shadow-lg z-20">
                    {/* User Info Section */}
                    <div className="px-4 py-4 border-b border-default">
                      <div className="flex items-center gap-3 mb-2">
                        {profile?.avatar_url ? (
                          <Image
                            src={profile.avatar_url}
                            alt={profile?.name || 'User'}
                            width={48}
                            height={48}
                            className="w-12 h-12 rounded-full object-cover"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-full bg-brand flex items-center justify-center flex-shrink-0">
                            <span className="text-white text-lg font-semibold">
                              {getInitials(profile?.name)}
                            </span>
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-primary truncate">
                            {profile?.name || 'User'}
                          </div>
                          <div className="text-xs text-secondary truncate">
                            {user?.email}
                          </div>
                        </div>
                      </div>
                      {profile?.role && (
                        <div className="inline-flex items-center px-2 py-1 rounded-md bg-accent text-xs font-medium text-brand capitalize">
                          {profile.role}
                        </div>
                      )}
                    </div>

                    {/* Navigation Section */}
                    <div className="py-1">
                      <Link href="/chat" onClick={() => setMenuOpen(false)}>
                        <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                          <span className="text-sm text-primary">Chat</span>
                        </div>
                      </Link>
                    </div>

                    <div className="border-t border-default"></div>

                    {/* Profile & Settings */}
                    <div className="py-1">
                      <Link href="/profile" onClick={() => setMenuOpen(false)}>
                        <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                          <span className="text-sm text-primary">Profile Settings</span>
                        </div>
                      </Link>
                    </div>

                    {/* Admin Links */}
                    {isAdmin && (
                      <>
                        <div className="border-t border-default"></div>
                        <div className="py-1">
                          <Link href="/admin/users" onClick={() => setMenuOpen(false)}>
                            <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                              <span className="text-sm text-primary">Users</span>
                            </div>
                          </Link>
                          <Link href="/admin/conversations" onClick={() => setMenuOpen(false)}>
                            <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                              <span className="text-sm text-primary">Conversations</span>
                            </div>
                          </Link>
                        </div>
                      </>
                    )}

                    <div className="border-t border-default"></div>

                    {/* Sign Out */}
                    <div className="py-1">
                      <button
                        onClick={handleSignOut}
                        className="w-full text-left px-4 py-2 hover:bg-hover cursor-pointer transition-colors"
                      >
                        <span className="text-sm text-red-600">Sign Out</span>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Centered Title */}
            <div className="absolute left-1/2 transform -translate-x-1/2 text-center">
              <h1 className="heading-2">Knowledge Base</h1>
            </div>

            {/* Empty right side for balance */}
            <div className="w-9"></div>
          </div>
        </div>
      </div>

      {/* Storage Indicator */}
      <div className="max-w-7xl mx-auto px-6 pt-3">
        <StorageIndicator
          apiBaseUrl={API_BASE_URL}
          refreshTrigger={storageRefreshTrigger}
          onStorageUpdate={(data) => {
            // Optional: Can add logic here if needed when storage updates
          }}
        />
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 pt-3 pb-8">
        {/* Google Drive Integration Section */}
        <div className={`card mb-3 ${driveExpanded && driveStatus?.connected ? 'p-6' : 'p-2'}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 flex-1">
              <button
                onClick={() => setDriveExpanded(!driveExpanded)}
                className="text-secondary hover:text-primary transition-colors"
              >
                {driveExpanded ? (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
              <h3 className="heading-3">Google Drive</h3>
            </div>
            {driveStatus && !driveStatus.connected && driveExpanded && (
              <button
                onClick={handleConnectDrive}
                className="btn-primary"
              >
                Connect Google Drive
              </button>
            )}
          </div>

          {driveExpanded && driveStatus?.connected && (
            <>
              <div className="mt-4 space-y-3">
                {/* Status and Actions */}
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm">
                    <div className="text-green-600 font-medium">Connected</div>
                    <div className="text-xs text-muted">
                      {driveStatus.document_count} documents • Last sync: {formatLastSync(driveStatus.last_sync)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleDisconnectClick}
                      className="btn-secondary text-red-600 hover:bg-red-50"
                    >
                      Disconnect
                    </button>
                  </div>
                </div>

                {/* Folder/File Selection and Picker */}
                <div className="bg-gray-50 border border-default rounded-lg p-3">
                  <label className="block text-sm font-medium text-secondary mb-2">
                    Paste the Google Drive file or folder URL
                  </label>
                  <div className="flex gap-2 mb-3">
                    <input
                      type="text"
                      value={selectedFolderId}
                      onChange={(e) => {
                        const value = e.target.value.trim()
                        // Extract folder or file ID from URL
                        const folderMatch = value.match(/folders\/([a-zA-Z0-9_-]+)/)
                        const fileMatch = value.match(/\/d\/([a-zA-Z0-9_-]+)/)

                        if (folderMatch) {
                          // It's a folder URL
                          const newFolderId = folderMatch[1]
                          setSelectedFolderId(newFolderId)
                          setIsFileUrl(false)
                          // Clear files when folder changes
                          if (newFolderId !== selectedFolderId) {
                            setDriveFiles([])
                            setSelectedDriveFileIds(new Set())
                          }
                        } else if (fileMatch) {
                          // It's a file URL - store the file ID
                          const fileId = fileMatch[1]
                          setSelectedFolderId(fileId)
                          setIsFileUrl(true)
                          // Clear folder files
                          setDriveFiles([])
                          setSelectedDriveFileIds(new Set())
                        } else {
                          // Just an ID (assume folder)
                          setSelectedFolderId(value)
                          setIsFileUrl(false)
                          if (value !== selectedFolderId) {
                            setDriveFiles([])
                            setSelectedDriveFileIds(new Set())
                          }
                        }
                      }}
                      placeholder="Folder or file URL (e.g., https://drive.google.com/file/d/...)"
                      className="flex-1 px-3 py-2 border border-default rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => {
                        if (isFileUrl) {
                          handleSyncSingleFile(selectedFolderId)
                        } else {
                          loadDriveFiles()
                        }
                      }}
                      disabled={!selectedFolderId || driveFilesLoading || syncing}
                      className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                    >
                      {driveFilesLoading ? 'Loading...' : syncing ? 'Syncing...' : isFileUrl ? 'Load File' : 'Load Folder'}
                    </button>
                    {selectedFolderId && (
                      <button
                        onClick={() => {
                          setSelectedFolderId('')
                          setDriveFiles([])
                          setSelectedDriveFileIds(new Set())
                          setIsFileUrl(false)
                        }}
                        className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  {/* File Picker */}
                  {driveFilesLoading ? (
                    <div className="text-sm text-muted py-4 text-center">
                      Loading files...
                    </div>
                  ) : driveFiles.length > 0 ? (
                    <>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-sm font-medium text-secondary">
                          Select Files to Sync
                        </label>
                        <div className="flex gap-2">
                          <button
                            onClick={selectAllDriveFiles}
                            className="text-xs text-blue-600 hover:text-blue-800"
                          >
                            Select All
                          </button>
                          <button
                            onClick={deselectAllDriveFiles}
                            className="text-xs text-gray-600 hover:text-gray-800"
                          >
                            Deselect All
                          </button>
                        </div>
                      </div>

                      <div className="max-h-64 overflow-y-auto space-y-2 bg-white rounded p-2">
                        {driveFiles.map(file => (
                          <label
                            key={file.id}
                            className="flex items-start gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={selectedDriveFileIds.has(file.id)}
                              onChange={() => toggleDriveFileSelection(file.id)}
                              className="mt-0.5"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-primary truncate">
                                {file.name}
                              </div>
                              <div className="text-xs text-muted">
                                {file.mimeType?.split('/').pop() || 'Unknown type'}
                                {file.size && ` • ${Math.round(parseInt(file.size) / 1024)} KB`}
                              </div>
                            </div>
                          </label>
                        ))}
                      </div>

                      {selectedDriveFileIds.size > 0 && (
                        <div className="mt-3 flex items-center justify-between">
                          <div className="text-xs text-muted">
                            {selectedDriveFileIds.size} file{selectedDriveFileIds.size === 1 ? '' : 's'} selected
                          </div>
                          <button
                            onClick={handleDriveFilesSync}
                            disabled={syncing}
                            className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {syncing ? 'Syncing...' : 'Sync Selected'}
                          </button>
                        </div>
                      )}
                    </>
                  ) : selectedFolderId && !isFileUrl && !driveFilesLoading ? (
                    <div className="text-sm text-muted py-4 text-center">
                      Click "Load Files" to see files in this folder
                    </div>
                  ) : null}
                </div>
              </div>

          {/* Sync Frequency Settings */}
          <div className="mt-4 border-t border-default pt-4">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium text-secondary">
                  Automatic Sync:
                </label>
                <select
                  value={syncFrequency}
                  onChange={(e) => handleSyncFrequencyChange(e.target.value)}
                  className="px-3 py-1.5 border border-default rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="manual">Manual Only</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
                {nextSyncScheduled && syncFrequency !== 'manual' && (
                  <span className="text-xs text-muted">
                    Next sync: {new Date(nextSyncScheduled).toLocaleString()}
                  </span>
                )}
              </div>
            </div>

          {/* Success Message */}
          {syncSuccess && (
            <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <span className="text-sm text-green-800">{syncSuccess}</span>
              </div>
            </div>
          )}

          {/* Error Message */}
          {syncError && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <span className="text-red-600">✗</span>
                <span className="text-sm text-red-800">{syncError}</span>
              </div>
            </div>
          )}

          {/* Syncing Progress */}
          {syncing && (
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <LoadingSpinner size="sm" />
                <span className="text-sm text-blue-800">Syncing documents from Google Drive...</span>
              </div>
            </div>
          )}
          </>
          )}
        </div>

        {/* Notion Integration Section */}
        <div className={`card mb-3 ${notionExpanded && notionStatus?.connected ? 'p-6' : 'p-2'}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 flex-1">
              <button
                onClick={() => setNotionExpanded(!notionExpanded)}
                className="text-secondary hover:text-primary transition-colors"
              >
                {notionExpanded ? (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
              <h3 className="heading-3">Notion</h3>
            </div>
            {notionStatus && !notionStatus.connected && notionExpanded && (
              <div className="flex gap-2">
                <button
                  onClick={handleConnectNotion}
                  className="btn-primary"
                >
                  Connect Notion
                </button>
                <button
                  onClick={async () => {
                    await checkNotionStatusFn()
                  }}
                  className="btn-secondary text-xs"
                  title="Refresh connection status"
                >
                  Refresh
                </button>
              </div>
            )}
          </div>

          {notionExpanded && notionStatus?.connected && (
            <>
              <div className="mt-4 space-y-3">
                {/* Status and Actions */}
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm">
                    <div className="text-green-600 font-medium">Connected</div>
                    <div className="text-xs text-muted">
                      {notionStatus.workspace_name} • {notionStatus.document_count} documents
                      {notionStatus.last_sync && ` • Last sync: ${formatLastSync(notionStatus.last_sync)}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleNotionDisconnectClick}
                      className="btn-secondary text-red-600 hover:bg-red-50"
                    >
                      Disconnect
                    </button>
                  </div>
                </div>

                {/* Page Picker */}
                <div className="bg-gray-50 border border-default rounded-lg p-3">
                  <div className="flex items-center justify-between mb-3">
                    <label className="block text-sm font-medium text-secondary">
                      Notion Pages
                    </label>
                    <button
                      onClick={loadNotionPages}
                      disabled={notionPagesLoading}
                      className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {notionPagesLoading ? 'Loading...' : 'Load Pages'}
                    </button>
                  </div>

                  {notionPages.length > 0 && (
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-secondary">
                        Select Pages to Sync
                      </label>
                      <div className="flex gap-2">
                        <button
                          onClick={selectAllNotionPages}
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          Select All
                        </button>
                        <button
                          onClick={deselectAllNotionPages}
                          className="text-xs text-gray-600 hover:text-gray-800"
                        >
                          Deselect All
                        </button>
                      </div>
                    </div>
                  )}

                  {notionPagesLoading ? (
                    <div className="text-sm text-muted py-4 text-center">
                      Loading pages...
                    </div>
                  ) : notionPages.length === 0 ? (
                    <div className="text-sm text-muted py-4 text-center">
                      No pages found. Make sure you've granted access to pages in Notion.
                    </div>
                  ) : (
                    <div className="max-h-64 overflow-y-auto space-y-2">
                      {notionPages.map(page => (
                        <label
                          key={page.id}
                          className="flex items-start gap-2 p-2 hover:bg-white rounded cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedNotionPageIds.has(page.id)}
                            onChange={() => toggleNotionPageSelection(page.id)}
                            className="mt-0.5"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-primary flex items-center gap-1">
                              {page.icon && <span>{page.icon}</span>}
                              <span className="truncate">{page.title}</span>
                            </div>
                            {page.url && (
                              <a
                                href={page.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-600 hover:text-blue-800 truncate block"
                                onClick={(e) => e.stopPropagation()}
                              >
                                View in Notion →
                              </a>
                            )}
                          </div>
                        </label>
                      ))}
                    </div>
                  )}

                  {selectedNotionPageIds.size > 0 && (
                    <div className="mt-3 flex items-center justify-between">
                      <div className="text-xs text-muted">
                        {selectedNotionPageIds.size} page{selectedNotionPageIds.size === 1 ? '' : 's'} selected
                      </div>
                      <button
                        onClick={handleNotionSync}
                        disabled={notionSyncing}
                        className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {notionSyncing ? 'Syncing...' : 'Sync Selected'}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Sync Frequency Settings */}
              <div className="mt-4 border-t border-default pt-4">
                <div className="flex items-center gap-4">
                  <label className="text-sm font-medium text-secondary">
                    Automatic Sync:
                  </label>
                  <select
                    value={notionSyncFrequency}
                    onChange={(e) => handleNotionSyncFrequencyChange(e.target.value)}
                    className="px-3 py-1.5 border border-default rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="manual">Manual Only</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                  {notionNextSyncScheduled && notionSyncFrequency !== 'manual' && (
                    <span className="text-xs text-muted">
                      Next sync: {new Date(notionNextSyncScheduled).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>

              {/* Success Message */}
              {notionSyncSuccess && (
                <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                        <span className="text-sm text-green-800">{notionSyncSuccess}</span>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {notionSyncError && (
                <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-red-600">✗</span>
                    <span className="text-sm text-red-800">{notionSyncError}</span>
                  </div>
                </div>
              )}

              {/* Syncing Progress */}
              {notionSyncing && (
                <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size="sm" />
                    <span className="text-sm text-blue-800">Syncing pages from Notion...</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Upload Section */}
        <div className={`card mb-3 ${uploadExpanded ? 'p-6' : 'p-2'}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 flex-1">
              <button
                onClick={() => setUploadExpanded(!uploadExpanded)}
                className="text-secondary hover:text-primary transition-colors"
              >
                {uploadExpanded ? (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
              <h3 className="heading-3">Upload</h3>
            </div>
          </div>

          {uploadExpanded && (
            <div className="mt-4">
              {profile?.client_id ? (
                <DocumentUpload
                  clientId={profile.client_id}
                  apiBaseUrl={API_BASE_URL}
                  onUploadComplete={handleDocumentsChange}
                />
              ) : (
                <p className="text-secondary">Loading...</p>
              )}
            </div>
          )}
        </div>

        {/* Documents List */}
        <div className={`card mb-3 ${documentsExpanded ? 'p-6' : 'p-2'}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 flex-1">
              <button
                onClick={() => setDocumentsExpanded(!documentsExpanded)}
                className="text-secondary hover:text-primary transition-colors"
              >
                {documentsExpanded ? (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
              <h2 className="heading-3">Documents</h2>
            </div>
          </div>

          {documentsExpanded && (
            <div className="mt-4">

            {/* General Document Notifications */}
            {generalSuccess && (
              <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-3">
                <div className="flex items-center gap-2">
                    <span className="text-sm text-green-800">{generalSuccess}</span>
                </div>
              </div>
            )}

            {generalError && (
              <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <span className="text-red-600">✗</span>
                  <span className="text-sm text-red-800">{generalError}</span>
                </div>
              </div>
            )}

            {loading ? (
              <div className="text-center py-8 text-muted">
                <LoadingSpinner size="md" />
                <p className="mt-2">Loading documents...</p>
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-sm">
                Error: {error}
              </div>
            ) : documents.filter(doc => !doc.is_core_document).length === 0 ? (
              <div className="text-center py-8 text-muted">
                <p>No documents uploaded yet</p>
                <p className="text-sm mt-2">Upload your first document to get started!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {/* Show sync progress indicators */}
                {syncing && (
                  <div className="border border-blue-200 bg-blue-50 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <LoadingSpinner size="sm" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-900 mb-2">Syncing from Google Drive:</p>
                        <div className="space-y-1">
                          {documents.filter(doc => !doc.processed && doc.source_platform === 'google_drive').map(doc => (
                            <div key={doc.id} className="flex items-center gap-2 text-sm text-blue-800">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Processing
                              </span>
                              <span className="truncate">{doc.filename}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {notionSyncing && (
                  <div className="border border-black bg-gray-50 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <LoadingSpinner size="sm" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 mb-2">Syncing from Notion:</p>
                        <div className="space-y-1">
                          {documents.filter(doc => !doc.processed && doc.source_platform === 'notion').map(doc => (
                            <div key={doc.id} className="flex items-center gap-2 text-sm text-gray-800">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Processing
                              </span>
                              <span className="truncate">{doc.filename}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {documents.filter(doc => !doc.is_core_document).map((doc) => (
                  <div
                    key={doc.id}
                    className={`border rounded-lg p-2 transition-colors ${
                      doc.is_core_document
                        ? 'border-gray-200 dark:border-green-700 bg-[#F1FEF4] dark:bg-green-900/20 hover:bg-[#E5F9E9] dark:hover:bg-green-900/30'
                        : 'border-default hover:bg-hover'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start gap-2 mb-1">
                          <h3 className="font-medium text-primary break-words">{doc.filename}</h3>
                          {/* Core Document Badge */}
                          {doc.is_core_document && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 flex-shrink-0" title="Core document - cannot be deleted">
                              ⭐ Core
                            </span>
                          )}
                          {/* Status Badges */}
                          {!doc.processed && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 flex-shrink-0" title="Document is being processed">
                              <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Processing
                            </span>
                          )}
                          {doc.processed && doc.processing_status === 'failed' && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 flex-shrink-0" title={`Processing failed: ${doc.processing_error || 'Unknown error'}`}>
                              ⚠️ Failed
                            </span>
                          )}
                          {doc.source_platform === 'google_drive' && (
                            <span className="inline-flex items-center gap-1 flex-shrink-0" title="Google Drive">
                              <Image src="/logos/google-drive.svg" alt="Google Drive" width={20} height={20} className="w-5 h-5" />
                            </span>
                          )}
                          {doc.source_platform === 'notion' && (
                            <span className="inline-flex items-center gap-1 flex-shrink-0" title="Notion">
                              <Image src="/logos/notion.svg" alt="Notion" width={20} height={20} className="w-5 h-5" />
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {/* Action Buttons */}
                        <div className="flex items-center gap-1">
                          {/* Sync Button - only for Google Drive docs */}
                          {doc.source_platform === 'google_drive' && (
                            <button
                              onClick={() => handleDocumentSync(doc)}
                              disabled={syncingDocId === doc.id}
                              className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Sync this document from Google Drive"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                              </svg>
                            </button>
                          )}

                          {/* Info Button */}
                          <button
                            onClick={() => handleDocumentInfo(doc)}
                            className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Document info"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          </button>

                          {/* Delete Button - hidden for core documents */}
                          {!doc.is_core_document && (
                            <button
                              onClick={() => handleDeleteClick(doc)}
                              disabled={deletingDocId === doc.id}
                              className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Delete document"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            </div>
          )}
        </div>

        {/* Core Documents List */}
        <div className={`card ${coreDocumentsExpanded ? 'p-6' : 'p-2'}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 flex-1">
              <button
                onClick={() => setCoreDocumentsExpanded(!coreDocumentsExpanded)}
                className="text-secondary hover:text-primary transition-colors"
              >
                {coreDocumentsExpanded ? (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
              <h2 className="heading-3 text-teal-600">Core Documents</h2>
            </div>
          </div>

          {coreDocumentsExpanded && (
            <div className="mt-4">
            {loading ? (
              <div className="text-center py-8 text-muted">
                <LoadingSpinner size="md" />
                <p className="mt-2">Loading documents...</p>
              </div>
            ) : documents.filter(doc => doc.is_core_document).length === 0 ? (
              <div className="text-center py-8 text-muted">
                <p>No core documents</p>
              </div>
            ) : (
              <div className="space-y-3">
                {documents.filter(doc => doc.is_core_document).map((doc) => (
                  <div
                    key={doc.id}
                    className="border border-default bg-card hover:bg-hover rounded-lg py-1.5 px-3 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-primary break-words text-sm">{doc.filename}</h3>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {/* Info Button */}
                        <button
                          onClick={() => handleDocumentInfo(doc)}
                          className="p-1 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                          title="Document info"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            </div>
          )}
        </div>

      </div>

      {/* Disconnect Confirmation Modal */}
      <ConfirmModal
        open={showDisconnectModal}
        title="Disconnect Google Drive"
        message="Are you sure you want to disconnect Google Drive? Synced documents will remain in your knowledge base."
        confirmText="Disconnect"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleDisconnectConfirm}
        onCancel={() => setShowDisconnectModal(false)}
      />

      {/* Notion Disconnect Confirmation Modal */}
      <ConfirmModal
        open={showNotionDisconnectModal}
        title="Disconnect Notion"
        message="Are you sure you want to disconnect Notion? Synced pages will remain in your knowledge base."
        confirmText="Disconnect"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleNotionDisconnectConfirm}
        onCancel={() => setShowNotionDisconnectModal(false)}
      />

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        open={showDeleteModal}
        title="Delete Document"
        message={`Are you sure you want to delete "${docToDelete?.filename}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleDeleteConfirm}
        onCancel={() => {
          setShowDeleteModal(false)
          setDocToDelete(null)
        }}
      />

      {/* Document Info Modal */}
      {showInfoModal && selectedDoc && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowInfoModal(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="heading-3">Document Information</h3>
              <button
                onClick={() => setShowInfoModal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-secondary">Filename</label>
                <p className="text-sm text-primary mt-1">{selectedDoc.filename}</p>
              </div>

              <div>
                <label className="text-sm font-medium text-secondary">Document ID</label>
                <p className="text-xs text-muted font-mono mt-1">{selectedDoc.id}</p>
              </div>

              <div>
                <label className="text-sm font-medium text-secondary">Source</label>
                <p className="text-sm text-primary mt-1">
                  {selectedDoc.source_platform === 'google_drive' ? 'Google Drive' : selectedDoc.source_platform === 'notion' ? 'Notion' : 'Direct Upload'}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-secondary">Uploaded</label>
                <p className="text-sm text-primary mt-1">{formatDate(selectedDoc.uploaded_at)}</p>
              </div>

              <div>
                <label className="text-sm font-medium text-secondary">File Size</label>
                <p className="text-sm text-primary mt-1">{formatFileSize(selectedDoc.file_size)}</p>
              </div>

              {selectedDoc.external_url && (
                <div>
                  <label className="text-sm font-medium text-secondary">External Link</label>
                  <a
                    href={selectedDoc.external_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:underline mt-1 inline-block"
                  >
                    View in Google Drive →
                  </a>
                </div>
              )}

              {/* Sync Cadence Setting - for Google Drive and Notion documents */}
              {(selectedDoc.source_platform === 'google_drive' || selectedDoc.source_platform === 'notion') && (
                <div className="border-t border-gray-200 pt-3 mt-3">
                  <label className="text-sm font-medium text-secondary block mb-2">
                    Automatic Sync Cadence
                  </label>
                  <select
                    value={tempSyncCadence}
                    onChange={(e) => setTempSyncCadence(e.target.value)}
                    className="w-full px-3 py-2 border border-default rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="manual">Manual Only</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                  <p className="text-xs text-muted mt-1">
                    Set how often this document should automatically sync from {selectedDoc.source_platform === 'google_drive' ? 'Google Drive' : 'Notion'}
                  </p>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2">
              {(selectedDoc.source_platform === 'google_drive' || selectedDoc.source_platform === 'notion') ? (
                <>
                  <button
                    onClick={() => setShowInfoModal(false)}
                    className="btn-secondary"
                  >
                    Close
                  </button>
                  <button
                    onClick={handleSaveDocumentInfo}
                    className="btn-primary"
                  >
                    Save
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setShowInfoModal(false)}
                  className="btn-secondary"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function DocumentsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-page flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    }>
      <DocumentsContent />
    </Suspense>
  )
}
