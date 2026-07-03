import { useEffect, useState } from 'react'
import { api, downloadZip } from '../api.js'

const PHASES = [
  ['vision', 'Анализ идеи'],
  ['roadmap', 'План'],
  ['architecture', 'Архитектура'],
  ['structure', 'Структура'],
  ['code', 'Код'],
  ['verify', 'Проверка'],
]

export default function Project({ projectId, onBack }) {
  const [project, setProject] = useState(null)
  const [artifacts, setArtifacts] = useState([])
  const [files, setFiles] = useState([])
  const [openArtifact, setOpenArtifact] = useState(null)
  const [openFile, setOpenFile] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let timer
    const load = async () => {
      try {
        const p = await api.getProject(projectId)
        setProject(p)
        setArtifacts(await api.getArtifacts(projectId))
        if (p.status === 'completed') setFiles(await api.getFiles(projectId))
        if (p.status === 'running') timer = setTimeout(load, 2000)
      } catch (err) {
        setError(err.message)
      }
    }
    load()
    return () => clearTimeout(timer)
  }, [projectId])

  if (error) return <div className="container"><div className="error">{error}</div></div>
  if (!project) return <div className="container muted">Загрузка…</div>

  const donePhases = new Set(artifacts.map((a) => a.phase))
  const rerun = async () => {
    await api.runProject(projectId)
    setArtifacts([])
    setFiles([])
    setProject({ ...project, status: 'running', current_phase: 'vision' })
    window.location.reload()
  }

  return (
    <div className="container">
      <button className="ghost" onClick={onBack}>← Все проекты</button>
      <div className="row">
        <h1>{project.name}</h1>
        <div className="row gap">
          {project.status === 'completed' && (
            <button className="primary" onClick={() => downloadZip(projectId, project.name)}>
              ⬇ Скачать ZIP
            </button>
          )}
          {(project.status === 'completed' || project.status === 'failed') && (
            <button className="ghost" onClick={rerun}>↻ Перегенерировать</button>
          )}
        </div>
      </div>
      <p className="muted">{project.idea}</p>
      {project.error && <div className="error">{project.error}</div>}

      <div className="phases">
        {PHASES.map(([key, label]) => {
          const isDone = donePhases.has(key)
          const isActive = project.status === 'running' && project.current_phase === key
          return (
            <div key={key} className={`phase ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}>
              {isDone ? '✓' : isActive ? '⟳' : '○'} {label}
            </div>
          )
        })}
      </div>

      <section>
        <h2>Артефакты</h2>
        {artifacts.length === 0 && <p className="muted">Агент ещё работает…</p>}
        {artifacts.map((a) => (
          <div key={a.id} className="card slim">
            <button
              className="row expander"
              onClick={() => setOpenArtifact(openArtifact === a.id ? null : a.id)}
            >
              <strong>{a.title}</strong>
              <span>{openArtifact === a.id ? '▾' : '▸'}</span>
            </button>
            {openArtifact === a.id && <pre className="doc">{a.content}</pre>}
          </div>
        ))}
      </section>

      {files.length > 0 && (
        <section>
          <h2>Файлы проекта ({files.length})</h2>
          {files.map((f) => (
            <div key={f.id} className="card slim">
              <button
                className="row expander"
                onClick={() => setOpenFile(openFile === f.id ? null : f.id)}
              >
                <code>{f.path}</code>
                <span>{openFile === f.id ? '▾' : '▸'}</span>
              </button>
              {openFile === f.id && <pre className="doc">{f.content}</pre>}
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
