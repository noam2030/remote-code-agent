import { useEffect, useState } from 'react'
import {
  generateCodeStream,
  getActiveRun,
  getFileContent,
  getLoadedSkills,
  getProject,
  listProjects,
  streamActiveRun,
} from './services/api'
import type { FileContentResponse, LoadedSkillsResponse, Project } from './types'

import { FilesDrawer } from './components/FilesDrawer'
import { FileViewerModal } from './components/FileViewerModal'
import { Header } from './components/Header'
import { MasterPromptModal } from './components/MasterPromptModal'
import { PromptEditor } from './components/PromptEditor'
import { Sidebar } from './components/Sidebar'
import { SkillsModal } from './components/SkillsModal'
import { TerminalStream } from './components/TerminalStream'

export function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [streamLogs, setStreamLogs] = useState('')
  const [mobileTab, setMobileTab] = useState<'console' | 'projects'>('console')

  // Modals & Drawers state
  const [filesDrawerOpen, setFilesDrawerOpen] = useState(false)
  const [activeFile, setActiveFile] = useState<FileContentResponse | null>(null)
  const [loadingFile, setLoadingFile] = useState(false)
  const [masterPromptFile, setMasterPromptFile] = useState<FileContentResponse | null>(null)
  const [loadingMasterPrompt, setLoadingMasterPrompt] = useState(false)
  const [skillsModalOpen, setSkillsModalOpen] = useState(false)
  const [skillsData, setSkillsData] = useState<LoadedSkillsResponse | null>(null)
  const [loadingSkills, setLoadingSkills] = useState(false)
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

  const fetchSkills = async () => {
    setLoadingSkills(true)
    try {
      const data = await getLoadedSkills()
      setSkillsData(data)
      return data
    } catch (err: any) {
      console.error('Failed to load skills:', err)
      return null
    } finally {
      setLoadingSkills(false)
    }
  }

  const handleOpenSkills = () => {
    setSkillsModalOpen(true)
    if (!skillsData) {
      fetchSkills()
    }
  }

  useEffect(() => {
    let isCancelled = false

    const init = async () => {
      fetchSkills()
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
          setMobileTab('console')
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

          // Stream actively in background without blocking init() completion
          streamActiveRun(run.logs ? run.logs.length : 0, (chunk) => {
            if (!isCancelled) {
              setStreamLogs((prev) => prev + chunk)
            }
          })
            .then(() => {
              if (!isCancelled) {
                showToast('Code generation finished!')
                fetchProjects()
                setIsGenerating(false)
              }
            })
            .catch((streamErr: any) => {
              console.error('Active stream error:', streamErr)
            })

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

  // Resilient fallback polling while a run is in progress
  useEffect(() => {
    if (!isGenerating) return

    const intervalId = setInterval(async () => {
      try {
        const run = await getActiveRun()
        if (!run) return

        if (run.status === 'completed' || run.status === 'error' || run.status === 'cancelled') {
          if (run.logs) {
            setStreamLogs((prev) => (run.logs!.length > prev.length ? run.logs! : prev))
          }
          setIsGenerating(false)
          fetchProjects()
          if (run.status === 'completed') {
            showToast('Code generation finished!')
          } else {
            showToast('Code generation ended: ' + run.status)
          }
        } else if (run.status === 'running' && run.logs) {
          setStreamLogs((prev) => (run.logs!.length > prev.length ? run.logs! : prev))
        }
      } catch {
        // Silently tolerate network blips
      }
    }, 3000)

    return () => clearInterval(intervalId)
  }, [isGenerating])

  useEffect(() => {
    const handleVisibilityChange = async () => {
      if (document.visibilityState === 'visible') {
        try {
          const run = await getActiveRun()
          if (run && run.status === 'running') {
            setMobileTab('console')
            if (run.logs) {
              setStreamLogs((prev) => (run.logs!.length > prev.length ? run.logs! : prev))
            }
            if (!isGenerating) {
              setIsGenerating(true)
              if (run.project_name && !selectedProject) {
                const found = projects.find(
                  (p) => p.name.toLowerCase() === run.project_name?.toLowerCase()
                )
                if (found) {
                  handleSelectProject(found)
                }
              }
              streamActiveRun(run.logs ? run.logs.length : 0, (chunk) => {
                setStreamLogs((prev) => prev + chunk)
              })
                .then(() => {
                  showToast('Code generation finished!')
                  fetchProjects()
                  setIsGenerating(false)
                })
                .catch((err: any) => {
                  console.error('Visibility change stream error:', err)
                })
            }
          } else if (run && run.status === 'completed' && isGenerating) {
            setIsGenerating(false)
            if (run.logs) {
              setStreamLogs((prev) => (run.logs!.length > prev.length ? run.logs! : prev))
            }
            fetchProjects()
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
  }, [isGenerating, projects, selectedProject])


  const handleSelectProject = async (proj: Project | null) => {
    setMobileTab('console')
    if (
      proj &&
      selectedProject &&
      proj.name.toLowerCase() !== selectedProject.name.toLowerCase() &&
      !isGenerating
    ) {
      setStreamLogs('')
    }
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
    setMobileTab('console')

    // Check if project already exists (case-insensitive)
    const existing = projects.find((p) => p.name.toLowerCase() === trimmed.toLowerCase())
    if (existing) {
      handleSelectProject(existing)
      showToast(`Selected existing project "${existing.name}".`)
      return
    }

    setStreamLogs('')
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

  const handleOpenMasterPrompt = async (projectName?: string) => {
    const target = projectName || selectedProject?.name
    if (!target) return
    setLoadingMasterPrompt(true)
    setMasterPromptFile(null)
    try {
      const res = await getFileContent(target, 'prompt.txt')
      setMasterPromptFile(res)
    } catch (err: any) {
      showToast(`Could not load prompt.txt: ${err.message}`)
    } finally {
      setLoadingMasterPrompt(false)
    }
  }

  const handleOpenProjectFiles = async (proj: Project) => {
    await handleSelectProject(proj)
    setFilesDrawerOpen(true)
  }

  const handleGenerate = async (prompt: string, targetProject?: string) => {
    setMobileTab('console')
    setIsGenerating(true)

    const currentOffset = streamLogs.length
    showToast('Executing agy CLI on remote container...')

    try {
      await generateCodeStream(
        prompt,
        targetProject,
        (chunk) => {
          setStreamLogs((prev) => prev + chunk)
        },
        undefined,
        currentOffset
      )
      showToast('agy CLI execution finished!')
      await fetchProjects()
    } catch (err: any) {
      setStreamLogs((prev) => prev + `\n\n❌ Error: ${err.message}\n`)
      showToast(`Execution error: ${err.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="app-layout">
      {toastMessage && <div className="app-toast">{toastMessage}</div>}

      <Header
        onOpenSkills={handleOpenSkills}
        skillsCount={skillsData?.skills_count ?? 0}
      />

      <nav className="mobile-view-tabs" aria-label="Mobile View Navigation">
        <button
          type="button"
          className={`mobile-tab-btn ${mobileTab === 'console' ? 'active' : ''}`}
          onClick={() => setMobileTab('console')}
        >
          <span>⚡ Live Console</span>
          {isGenerating && <span className="tab-live-badge">Running</span>}
        </button>
        <button
          type="button"
          className={`mobile-tab-btn ${mobileTab === 'projects' ? 'active' : ''}`}
          onClick={() => setMobileTab('projects')}
        >
          <span>📁 Projects ({projects.length})</span>
        </button>
      </nav>

      <main className={`main-grid mobile-tab-${mobileTab}`}>
        <Sidebar
          projects={projects}
          selectedProject={selectedProject}
          loading={loadingProjects}
          onSelectProject={handleSelectProject}
          onCreateProject={handleCreateProject}
          onRefresh={fetchProjects}
          onOpenProjectFiles={handleOpenProjectFiles}
          onOpenMasterPrompt={(proj) => handleOpenMasterPrompt(proj.name)}
        />

        <section className="content-area">
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

      <SkillsModal
        isOpen={skillsModalOpen}
        skillsData={skillsData}
        loading={loadingSkills}
        onClose={() => setSkillsModalOpen(false)}
        onRefresh={fetchSkills}
      />
    </div>
  )
}

export default App
