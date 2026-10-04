import { useEffect, useState } from 'react'
import {
  deleteProject,
  generateCodeStream,
  getFileContent,
  getProject,
  listProjects,
} from './services/api'
import type { FileContentResponse, Project } from './types'

import { DeleteModal } from './components/DeleteModal'
import { FilesDrawer } from './components/FilesDrawer'
import { FileViewerModal } from './components/FileViewerModal'
import { Header } from './components/Header'
import { MasterPromptModal } from './components/MasterPromptModal'
import { PromptEditor } from './components/PromptEditor'
import { SettingsModal } from './components/SettingsModal'
import { Sidebar } from './components/Sidebar'
import { TerminalStream } from './components/TerminalStream'

export function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [streamLogs, setStreamLogs] = useState('')

  // Modals & Drawers state
  const [filesDrawerOpen, setFilesDrawerOpen] = useState(false)
  const [activeFile, setActiveFile] = useState<FileContentResponse | null>(null)
  const [loadingFile, setLoadingFile] = useState(false)
  const [masterPromptFile, setMasterPromptFile] = useState<FileContentResponse | null>(null)
  const [loadingMasterPrompt, setLoadingMasterPrompt] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deletingProject, setDeletingProject] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3500)
  }

  const fetchProjects = async () => {
    setLoadingProjects(true)
    try {
      const data = await listProjects()
      setProjects(data)
      // Keep selected project updated
      if (selectedProject) {
        const found = data.find((p) => p.name === selectedProject.name)
        if (found) setSelectedProject(found)
      }
    } catch (err: any) {
      showToast(`Error fetching projects: ${err.message}`)
    } finally {
      setLoadingProjects(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleSelectProject = async (proj: Project | null) => {
    setSelectedProject(proj)
    if (proj) {
      try {
        const detail = await getProject(proj.name)
        setSelectedProject(detail)
      } catch (err) {
        // Fallback to existing summary
      }
    }
  }

  const handleOpenFile = async (filePath: string) => {
    if (!selectedProject) return
    setLoadingFile(true)
    setActiveFile(null)
    try {
      const res = await getFileContent(selectedProject.name, filePath)
      setActiveFile(res)
    } catch (err: any) {
      showToast(`Failed to open file: ${err.message}`)
    } finally {
      setLoadingFile(false)
    }
  }

  const handleOpenMasterPrompt = async () => {
    if (!selectedProject) return
    setLoadingMasterPrompt(true)
    setMasterPromptFile(null)
    try {
      const res = await getFileContent(selectedProject.name, 'prompt.txt')
      setMasterPromptFile(res)
    } catch (err: any) {
      showToast(`Could not load prompt.txt: ${err.message}`)
    } finally {
      setLoadingMasterPrompt(false)
    }
  }

  const handleDeleteConfirm = async (deleteRemote: boolean) => {
    if (!selectedProject) return
    setDeletingProject(true)
    try {
      const res = await deleteProject(selectedProject.name, deleteRemote)
      showToast(res.message || `Deleted project '${selectedProject.name}'`)
      setSelectedProject(null)
      setDeleteModalOpen(false)
      await fetchProjects()
    } catch (err: any) {
      showToast(`Failed to delete: ${err.message}`)
    } finally {
      setDeletingProject(false)
    }
  }

  const handleGenerate = async (prompt: string, targetProject?: string) => {
    setIsGenerating(true)
    setStreamLogs('')
    showToast('Starting code generation...')

    try {
      await generateCodeStream(prompt, targetProject, (chunk) => {
        setStreamLogs((prev) => prev + chunk)
      })
      showToast('Code generation finished!')
      await fetchProjects()
    } catch (err: any) {
      setStreamLogs((prev) => prev + `\n\n❌ Error: ${err.message}\n`)
      showToast(`Generation error: ${err.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="app-layout">
      {toastMessage && <div className="app-toast">{toastMessage}</div>}

      <Header
        project={selectedProject}
        onToggleFiles={() => setFilesDrawerOpen((prev) => !prev)}
        onOpenMasterPrompt={handleOpenMasterPrompt}
        onOpenDelete={() => setDeleteModalOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
        filesOpen={filesDrawerOpen}
      />

      <div className="app-body">
        <Sidebar
          projects={projects}
          selectedProject={selectedProject}
          loading={loadingProjects}
          onSelectProject={handleSelectProject}
          onRefresh={fetchProjects}
        />

        <main className="main-content">
          <PromptEditor
            selectedProject={selectedProject}
            isGenerating={isGenerating}
            onSubmit={handleGenerate}
          />

          <TerminalStream
            logs={streamLogs}
            isGenerating={isGenerating}
            onClear={() => setStreamLogs('')}
          />
        </main>

        <FilesDrawer
          project={selectedProject}
          isOpen={filesDrawerOpen}
          onClose={() => setFilesDrawerOpen(false)}
          onOpenFile={handleOpenFile}
        />
      </div>

      <FileViewerModal
        file={activeFile}
        loading={loadingFile}
        onClose={() => setActiveFile(null)}
      />

      <MasterPromptModal
        promptFile={masterPromptFile}
        loading={loadingMasterPrompt}
        onClose={() => setMasterPromptFile(null)}
      />

      <DeleteModal
        isOpen={deleteModalOpen}
        projectName={selectedProject?.name || null}
        loading={deletingProject}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteModalOpen(false)}
      />

      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSave={() => {
          showToast('Backend URL updated')
          fetchProjects()
        }}
      />
    </div>
  )
}

export default App
