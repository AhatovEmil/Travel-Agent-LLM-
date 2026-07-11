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
  const [linkedLocal, setLinkedLocal] = useState(false)

  useEffect(() => {
    if (!open) return
    setDetail(initialDetail)
    setLinkMsg('')
    setLinkedLocal(Boolean(initialDetail?.telegram_linked ?? quota?.telegram_linked))
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

    // свежий статус привязки с /me
    api
      .me()
      .then((u) => {
        setLinkedLocal(Boolean(u.telegram_linked))
        setDetail((prev) => ({
          ...(prev || {}),
          telegram_linked: u.telegram_linked,
          free_left: u.free_left,
          free_limit: u.free_limit,
          credits: u.credit_balance,
          credit_balance: u.credit_balance,
        }))
      })
      .catch(() => {})
  }, [open, initialDetail, quota?.telegram_linked])

  const linked = linkedLocal || Boolean(detail?.telegram_linked ?? quota?.telegram_linked)

  useEffect(() => {
    if (!open || !botUsername || linked) return
    const scriptId = 'telegram-login-script'
    const existing = document.getElementById(scriptId)
    if (existing) existing.remove()
    const script = document.createElement('script')
    script.id = scriptId
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.setAttribute('data-telegram-login', botUsername)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-radius', '10')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    const slot = document.getElementById('tg-login-slot')
    if (slot) {
      slot.innerHTML = ''
      slot.appendChild(script)
    }
  }, [open, botUsername, linked])

  useEffect(() => {
    const handler = async (e) => {
      const user = e.detail
      if (!user?.id || !user?.hash) return
      setLinkBusy(true)
      setLinkMsg('')
      try {
        const res = await api.linkTelegramWidget(user)
        setLinkedLocal(true)
        setDetail((prev) => ({
          ...(prev || {}),
          telegram_linked: true,
          credits: res.credit_balance,
          credit_balance: res.credit_balance,
        }))
        setLinkMsg(
          res.credits_claimed > 0
            ? `Telegram привязан. Начислено ${res.credits_claimed} генераций — можно покупать ещё.`
            : 'Telegram привязан. Теперь доступна оплата пакетов.',
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

        {!linked ? (
          <div className="quota-tg-block">
            <h3 className="quota-tg-title">Шаг 1. Привяжите Telegram</h3>
            <p className="muted small">
              Сначала войдите через Telegram — иначе оплата не попадёт на аккаунт. Кнопки покупки
              появятся после привязки.
            </p>
            <div id="tg-login-slot" className="tg-login-slot" />
            {!botUsername ? (
              <p className="muted small">Виджет не настроен (TELEGRAM_BOT_USERNAME).</p>
            ) : null}
            {linkBusy ? <p className="muted small">Привязка…</p> : null}
            {linkMsg ? <p className="quota-link-msg">{linkMsg}</p> : null}
            <div className="quota-modal-actions" style={{ marginTop: 14 }}>
              <button type="button" className="ghost" onClick={onClose}>
                Закрыть
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="quota-tg-block">
              <h3 className="quota-tg-title">Telegram привязан</h3>
              <p className="muted small">✓ Можно покупать пакеты — начисление автоматическое.</p>
              {linkMsg ? <p className="quota-link-msg">{linkMsg}</p> : null}
            </div>

            <h3 className="quota-tg-title">Шаг 2. Купить генерации</h3>
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
              Бот пришлёт ссылку Tribute (карта / СБП). После оплаты кредиты появятся здесь.
            </p>
            <div className="quota-modal-actions">
              <a className="primary" href={botUrl} target="_blank" rel="noreferrer">
                Открыть бота
              </a>
              <button type="button" className="ghost" onClick={onClose}>
                Закрыть
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

/** Кнопка-счётчик в шапке */
export function QuotaBadge({ quota, onClick }) {
  if (!quota) return null
  const { free_left: left, free_limit: limit, credit_balance: credits, telegram_linked: linked } =
    quota
  const parts = [`${left}/${limit}`]
  if (credits > 0) parts.push(`+${credits}`)
  if (!linked) parts.push('TG')
  return (
    <button
      type="button"
      className={`ghost compact quota-badge${!linked ? ' quota-badge-warn' : ''}`}
      onClick={onClick}
      title={
        linked
          ? 'Лимит генераций и покупка'
          : 'Сначала привяжите Telegram'
      }
    >
      {parts.join(' · ')}
    </button>
  )
}
