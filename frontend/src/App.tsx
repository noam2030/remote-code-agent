import { useEffect, useState } from 'react'
import {
  generateCodeStream,
  getActiveRun,
  getFileContent,
  getProject,
  listProjects,
  streamActiveRun,
} from './services/api'
import type { FileContentResponse, Project } from './types'

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
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3500)
  }

  const fetchProjects = async () => {
    setLoadingProjects(true)
    try {
      const data = await listProjects()
      if (selectedProject) {
        const found = data.find((p) => p.name.toLowerCase() === selectedProject.name.toLowerCase())
        if (found) {
          setSelectedProject(found)
          setProjects(data)
        } else if (!selectedProject.has_remote && !selectedProject.is_local) {
          // Keep active newly created project at top of list
          setProjects([selectedProject, ...data.filter((p) => p.name.toLowerCase() !== selectedProject.name.toLowerCase())])
        } else {
          setProjects(data)
        }
      } else {
        setProjects(data)
      }
      return data
    } catch (err: any) {
      showToast(`Error fetching projects: ${err.message}`)
      return []
    } finally {
      setLoadingProjects(false)
    }
  }

  useEffect(() => {
    let isCancelled = false

    const init = async () => {
      setLoadingProjects(true)
      let data: Project[] = []
      try {
        data = await listProjects()
        if (!isCancelled) {
          setProjects(data)
        }
      } catch (err: any) {
        showToast(`Error fetching projects: ${err.message}`)
      } finally {
        if (!isCancelled) {
          setLoadingProjects(false)
        }
      }

      // Check for active or recently finished background run
      try {
        const run = await getActiveRun()
        if (isCancelled) return

        if (run && run.status === 'running') {
          setIsGenerating(true)
          if (run.logs) {
            setStreamLogs(run.logs)
          }

          if (run.project_name) {
            const found = data.find(
              (p) => p.name.toLowerCase() === run.project_name?.toLowerCase()
            )
            if (found) {
              handleSelectProject(found)
            } else {
              setSelectedProject({
                name: run.project_name,
                github_url: `https://github.com/noam2030/${run.project_name}`,
                cloud_run_url: null,
                vercel_url: null,
                has_remote: true,
                is_local: true,
                files: [],
                files_detail: [],
                lines_of_code: 0,
                tokens_spent: 0,
                files_count: 0,
                stats: {},
              })
            }
          }

          showToast(`Connected to active run for project '${run.project_name || 'current'}'`)

          try {
            await streamActiveRun(run.logs ? run.logs.length : 0, (chunk) => {
              if (!isCancelled) {
                setStreamLogs((prev) => prev + chunk)
              }
            })
            if (!isCancelled) {
              showToast('Code generation finished!')
              fetchProjects()
            }
          } catch (streamErr: any) {
            console.error('Active stream error:', streamErr)
          } finally {
            if (!isCancelled) {
              setIsGenerating(false)
            }
          }
          return
        } else if (run && run.status === 'completed' && run.logs) {
          setStreamLogs(run.logs)
          if (run.project_name) {
            const found = data.find(
              (p) => p.name.toLowerCase() === run.project_name?.toLowerCase()
            )
            if (found) {
              handleSelectProject(found)
              return
            }
          }
        }
      } catch {
        // Active run check failed or endpoint unavailable
      }

      if (data.length > 0) {
        handleSelectProject(data[0])
      }
    }

    init()

    return () => {
      isCancelled = true
    }
  }, [])

  useEffect(() => {
    const handleVisibilityChange = async () => {
      if (document.visibilityState === 'visible' && !isGenerating) {
        try {
          const run = await getActiveRun()
          if (run && run.status === 'running') {
            setIsGenerating(true)
            if (run.logs) {
              setStreamLogs(run.logs)
            }
            if (run.project_name) {
              const found = projects.find(
                (p) => p.name.toLowerCase() === run.project_name?.toLowerCase()
              )
              if (found) {
                handleSelectProject(found)
              }
            }
            try {
              await streamActiveRun(run.logs ? run.logs.length : 0, (chunk) => {
                setStreamLogs((prev) => prev + chunk)
              })
              showToast('Code generation finished!')
              fetchProjects()
            } catch (err: any) {
              console.error('Stream error:', err)
            } finally {
              setIsGenerating(false)
            }
          }
        } catch {
          // ignore
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [isGenerating, projects])


  const handleSelectProject = async (proj: Project | null) => {
    setSelectedProject(proj)
    if (proj && (proj.has_remote || proj.is_local || (proj.files_count ?? 0) > 0)) {
      try {
        const detail = await getProject(proj.name)
        if (detail) {
          setSelectedProject(detail)
        }
      } catch {
        // Fallback to existing summary
      }
    }
  }

  const handleCreateProject = (name: string) => {
    const trimmed = name.trim()
    if (!trimmed) return

    // Check if project already exists (case-insensitive)
    const existing = projects.find((p) => p.name.toLowerCase() === trimmed.toLowerCase())
    if (existing) {
      handleSelectProject(existing)
      showToast(`Selected existing project "${existing.name}".`)
      return
    }

    const newProj: Project = {
      name: trimmed,
      cloud_run_url: null,
      vercel_url: null,
      github_url: `https://github.com/noam2030/${trimmed}`,
      has_remote: false,
      is_local: false,
      files: [],
      files_detail: [],
      lines_of_code: 0,
      tokens_spent: 0,
      files_count: 0,
      stats: {},
      description: 'New project ready for code generation',
    }

    setProjects((prev) => [newProj, ...prev.filter((p) => p.name.toLowerCase() !== trimmed.toLowerCase())])
    setSelectedProject(newProj)
    showToast(`Project "${trimmed}" created! Enter your prompt below to generate code.`)
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
          onCreateProject={handleCreateProject}
          onRefresh={fetchProjects}
        />

        <section className="content-area">
          <TargetProjectBanner
            project={selectedProject}
            filesCount={filesCount}
            filesOpen={filesDrawerOpen}
            onToggleFiles={() => setFilesDrawerOpen((prev) => !prev)}
            onOpenMasterPrompt={handleOpenMasterPrompt}
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
    </div>
  )
}

export default App
