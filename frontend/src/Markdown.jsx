/** Рендер Markdown в чистый HTML: заголовки, списки, чекбоксы, жирный/курсив. */

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function inlineFormat(text) {
  let s = escapeHtml(text)
  // жирный: **текст** или __текст__
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/__(.+?)__/g, '<strong>$1</strong>')
  // курсив: *текст* или _текст_ (не трогаем уже обработанное)
  s = s.replace(/(^|[^*])\*([^*\n]+?)\*(?!\*)/g, '$1<em>$2</em>')
  s = s.replace(/(^|[^_])_([^_\n]+?)_(?!_)/g, '$1<em>$2</em>')
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>')
  // убрать одиночные маркеры, если LLM оставил мусор
  s = s.replace(/(^|\s)#{1,6}\s+/g, '$1')
  s = s.replace(/\*\*/g, '')
  s = s.replace(/__/g, '')
  return s
}

function cleanHeadingText(text) {
  return text.replace(/^#+\s*/, '').trim()
}

export default function Markdown({ children }) {
  const source = typeof children === 'string' ? children : ''
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const html = []
  let inUl = false
  let inOl = false

  const closeLists = () => {
    if (inUl) {
      html.push('</ul>')
      inUl = false
    }
    if (inOl) {
      html.push('</ol>')
      inOl = false
    }
  }

  for (const raw of lines) {
    const line = raw.trimEnd()
    const trimmed = line.trim()
    if (!trimmed) {
      closeLists()
      continue
    }
    if (/^---+$/.test(trimmed)) {
      closeLists()
      html.push('<hr />')
      continue
    }

    // #### Заголовок → h2–h4 (слишком глубокие уровни схлопываем)
    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      closeLists()
      const level = Math.min(Math.max(heading[1].length, 1), 4)
      const title = cleanHeadingText(heading[2])
      html.push(`<h${level}>${inlineFormat(title)}</h${level}>`)
      continue
    }

    if (trimmed.startsWith('> ')) {
      closeLists()
      html.push(`<blockquote>${inlineFormat(trimmed.slice(2))}</blockquote>`)
      continue
    }

    const check = trimmed.match(/^[-*+]\s+\[([ xX])\]\s+(.+)$/)
    if (check) {
      if (!inUl) {
        closeLists()
        html.push('<ul class="task-list">')
        inUl = true
      }
      const checked = check[1].toLowerCase() === 'x' ? ' checked' : ''
      html.push(
        `<li><label><input type="checkbox" disabled${checked} /> ${inlineFormat(check[2])}</label></li>`,
      )
      continue
    }

    const bullet = trimmed.match(/^[-*+]\s+(.+)$/)
    if (bullet) {
      if (!inUl) {
        closeLists()
        html.push('<ul>')
        inUl = true
      }
      html.push(`<li>${inlineFormat(bullet[1])}</li>`)
      continue
    }

    const numbered = trimmed.match(/^\d+[.)]\s+(.+)$/)
    if (numbered) {
      if (!inOl) {
        closeLists()
        html.push('<ol>')
        inOl = true
      }
      html.push(`<li>${inlineFormat(numbered[1])}</li>`)
      continue
    }

    closeLists()
    html.push(`<p>${inlineFormat(trimmed)}</p>`)
  }
  closeLists()

  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html.join('\n') }} />
}
