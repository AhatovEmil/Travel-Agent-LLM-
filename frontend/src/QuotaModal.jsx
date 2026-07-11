import { useEffect, useState } from 'react'
import { api } from './api.js'

function formatPrice(rub) {
  return new Intl.NumberFormat('ru-RU').format(rub) + ' ₽'
}

function onTelegramAuth(user) {
  window.dispatchEvent(new CustomEvent('travel-tg-auth', { detail: user }))
}

// Telegram Login Widget callback must be global
if (typeof window !== 'undefined') {
  window.onTelegramAuth = onTelegramAuth
}

export default function QuotaModal({ open, onClose, initialDetail = null, quota = null, onLinked }) {
  const [detail, setDetail] = useState(initialDetail)
  const [loading, setLoading] = useState(false)
  const [linkBusy, setLinkBusy] = useState(false)
  const [linkMsg, setLinkMsg] = useState('')
  const [botUsername, setBotUsername] = useState('')

  useEffect(() => {
    if (!open) return
    setDetail(initialDetail)
    setLinkMsg('')
    setLoading(true)
    api
      .billingPackages()
      .then((data) => {
        setBotUsername(data.bot_username || '')
        setDetail((prev) => ({
          ...(prev || {}),
          packages: data.packages,
          telegram_url: data.telegram_url,
          bot_url: data.bot_url,
          free_limit: data.free_generations_per_month,
          tribute_configured: data.tribute_configured,
        }))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [open, initialDetail])

  useEffect(() => {
    if (!open || !botUsername) return
    const scriptId = 'telegram-login-script'
    const existing = document.getElementById(scriptId)
    if (existing) existing.remove()
    const script = document.createElement('script')
    script.id = scriptId
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.setAttribute('data-telegram-login', botUsername)
    script.setAttribute('data-size', 'medium')
    script.setAttribute('data-radius', '10')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    const slot = document.getElementById('tg-login-slot')
    if (slot) {
      slot.innerHTML = ''
      slot.appendChild(script)
    }
  }, [open, botUsername, detail?.telegram_linked])

  useEffect(() => {
    const handler = async (e) => {
      const user = e.detail
      if (!user?.id || !user?.hash) return
      setLinkBusy(true)
      setLinkMsg('')
      try {
        const res = await api.linkTelegramWidget(user)
        setLinkMsg(
          res.credits_claimed > 0
            ? `Telegram привязан. Начислено ${res.credits_claimed} генераций.`
            : 'Telegram привязан. Можно оплачивать пакеты.',
        )
        onLinked?.(res)
      } catch (err) {
        setLinkMsg(err.message || 'Не удалось привязать Telegram')
      } finally {
        setLinkBusy(false)
      }
    }
    window.addEventListener('travel-tg-auth', handler)
    return () => window.removeEventListener('travel-tg-auth', handler)
  }, [onLinked])

  if (!open) return null

  const packages = detail?.packages || []
  const botUrl = detail?.bot_url || detail?.telegram_url || 'https://t.me/'
  const freeLeft = detail?.free_left ?? quota?.free_left ?? 0
  const freeLimit = detail?.free_limit ?? quota?.free_limit ?? 5
  const credits = detail?.credits ?? detail?.credit_balance ?? quota?.credit_balance ?? 0
  const linked = Boolean(detail?.telegram_linked ?? quota?.telegram_linked)

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-card quota-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="quota-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="quota-title">Лимит генераций</h2>
        <p className="quota-modal-lead">
          Бесплатно: {freeLeft} из {freeLimit} в этом месяце
          {credits > 0 ? ` · кредиты: ${credits}` : ''}.
          Полный запуск плана списывает 1 генерацию.
        </p>

        <div className="quota-tg-block">
          {linked ? (
            <p className="muted small">Telegram привязан — оплаты Tribute начислятся автоматически.</p>
          ) : (
            <>
              <p className="muted small">
                Сначала привяжите Telegram, затем купите пакет в боте (ссылка Tribute).
              </p>
              <div id="tg-login-slot" className="tg-login-slot" />
              {!botUsername ? (
                <p className="muted small">Виджет входа появится после настройки TELEGRAM_BOT_USERNAME.</p>
              ) : null}
            </>
          )}
          {linkBusy ? <p className="muted small">Привязка…</p> : null}
          {linkMsg ? <p className="quota-link-msg">{linkMsg}</p> : null}
        </div>

        {loading ? <p className="muted">Загрузка пакетов…</p> : null}
        <ul className="quota-packages">
          {packages.map((p) => {
            const href = p.buy_url || botUrl
            return (
              <li key={p.id}>
                <div>
                  <strong>{p.label}</strong>
                  <span className="muted">{formatPrice(p.price_rub)}</span>
                </div>
                <a className="primary compact" href={href} target="_blank" rel="noreferrer">
                  Купить в боте
                </a>
              </li>
            )
          })}
        </ul>
        <p className="muted small">
          Бот пришлёт ссылку на оплату в Tribute (карта / СБП). После оплаты кредиты появятся на
          сайте.
        </p>
        <div className="quota-modal-actions">
          <a className="primary" href={botUrl} target="_blank" rel="noreferrer">
            Открыть бота
          </a>
          <button type="button" className="ghost" onClick={onClose}>
            Закрыть
          </button>
        </div>
      </div>
    </div>
  )
}

/** Кнопка-счётчик в шапке */
export function QuotaBadge({ quota, onClick }) {
  if (!quota) return null
  const { free_left: left, free_limit: limit, credit_balance: credits } = quota
  const label = credits > 0 ? `${left}/${limit} · +${credits}` : `${left}/${limit}`
  return (
    <button
      type="button"
      className="ghost compact quota-badge"
      onClick={onClick}
      title="Лимит генераций плана в месяц"
    >
      {label}
    </button>
  )
}
