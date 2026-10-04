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
import { Sidebar } from './components/Sidebar'
import { TargetProjectBanner } from './components/TargetProjectBanner'
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
      if (selectedProject) {
        const found = data.find((p) => p.name === selectedProject.name)
        if (found) setSelectedProject(found)
      } else if (data.length > 0) {
        // Auto-select first project if none selected
        handleSelectProject(data[0])
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
      } catch {
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

  const filesCount =
    selectedProject?.files_count ||
    (selectedProject?.files_detail ? selectedProject.files_detail.length : 0) ||
    (selectedProject?.files ? selectedProject.files.length : 0)

  return (
    <div className="app-layout">
      {toastMessage && <div className="app-toast">{toastMessage}</div>}

      <Header />

      <main className="main-grid">
        <Sidebar
          projects={projects}
          selectedProject={selectedProject}
          loading={loadingProjects}
          onSelectProject={handleSelectProject}
          onRefresh={fetchProjects}
          onDeleteProject={(proj) => {
            setSelectedProject(proj)
            setDeleteModalOpen(true)
          }}
        />

        <section className="content-area">
          <TargetProjectBanner
            project={selectedProject}
            filesCount={filesCount}
            filesOpen={filesDrawerOpen}
            onToggleFiles={() => setFilesDrawerOpen((prev) => !prev)}
            onOpenMasterPrompt={handleOpenMasterPrompt}
            onOpenDelete={() => setDeleteModalOpen(true)}
          />

          <FilesDrawer
            project={selectedProject}
            isOpen={filesDrawerOpen}
            onOpenFile={handleOpenFile}
          />

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
        </section>
      </main>

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
    </div>
  )
}

export default App
