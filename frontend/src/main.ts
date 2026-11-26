import './assets/main.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { installAuthInterceptors } from './api/authInterceptor'
import { http } from './api/http'
import { queryClient } from './api/queryClient'
import router from './router'
import { createAuthGuard } from './router/guards'
import { useAuthStore } from './stores/auth'

const app = createApp(App)

app.use(createPinia())
const auth = useAuthStore()

installAuthInterceptors(http, {
  getToken: () => auth.accessToken,
  refresh: () => auth.refreshAccessToken(),
  onSessionExpired: () => {
    auth.clear()
    queryClient.clear()
    void router.push({
      name: 'login',
      query: { reason: 'expired', redirect: router.currentRoute.value.fullPath },
    })
  },
})
router.beforeEach(createAuthGuard(auth))

app.use(router)
app.use(VueQueryPlugin, { queryClient })

app.mount('#app')
