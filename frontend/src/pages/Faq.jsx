import { useState } from 'react'

const FAQ_ITEMS = [
  {
    q: 'Что это за сервис?',
    a: 'Travel Agent собирает черновик поездки: план по дням, бюджет и чеклист. Дальше вы правите план и бронируете жильё/билеты по ссылкам сами.',
  },
  {
    q: 'Цены и адреса точные?',
    a: 'Нет — это ориентиры от ИИ. Перед бронью и выездом сверяйте часы работы, маршруты и стоимость на официальных сайтах.',
  },
  {
    q: 'Нужен ли ключ DeepSeek?',
    a: 'На публичном сайте ключ уже настроен на сервере. Если поднимаете проект сами — ключ DeepSeek нужен в файле .env (см. README).',
  },
  {
    q: 'Где жильё и билеты?',
    a: 'На странице поездки блок «Жильё и билеты» вверху — один раз на всю поездку. Ссылки открывают поиск по городу и датам, не главную сайта.',
  },
  {
    q: 'Что такое режимы План / На месте / Воспоминания?',
    a: 'План — документы и маршрут. На месте — брифинг дня, live и Street Smart. Воспоминания — дневник и вечерние чекины.',
  },
  {
    q: 'Как поделиться с друзьями?',
    a: 'Кнопка «Ссылка для друзей» на готовой поездке. По ссылке можно голосовать за слоты; владелец потом пересоберёт план по голосам.',
  },
  {
    q: 'Почему PDF иногда не скачивался?',
    a: 'На сервере нужны шрифты с кириллицей (DejaVu). В актуальном Docker-образе они уже ставятся автоматически.',
  },
  {
    q: 'Это open source?',
    a: 'Да, код на GitHub под MIT. Не коммитьте .env с ключами — только шаблон .env.example.',
  },
]

export default function Faq({ onBack }) {
  const [open, setOpen] = useState(0)

  return (
    <div className="container faq-page">
      <div className="page-hero faq-hero">
        <p className="hero-kicker">Travel Agent</p>
        <h1>Частые вопросы</h1>
        <p className="muted">Коротко о том, как устроен сервис и чего от него ждать.</p>
        {onBack && (
          <button type="button" className="ghost compact" onClick={onBack}>
            ← К поездкам
          </button>
        )}
      </div>

      <div className="faq-list">
        {FAQ_ITEMS.map((item, idx) => {
          const isOpen = open === idx
          return (
            <div key={item.q} className={`faq-item ${isOpen ? 'open' : ''}`}>
              <button
                type="button"
                className="faq-q"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? -1 : idx)}
              >
                <span>{item.q}</span>
                <span className="faq-chevron" aria-hidden="true">
                  {isOpen ? '−' : '+'}
                </span>
              </button>
              {isOpen && <p className="faq-a">{item.a}</p>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
