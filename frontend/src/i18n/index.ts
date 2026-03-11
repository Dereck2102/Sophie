import { createI18n } from 'vue-i18n'
import es from './es'
import en from './en'

const savedLocale = localStorage.getItem('sophie_locale') ?? 'es'

export const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'es',
  messages: { es, en },
})

export default i18n
