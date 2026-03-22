import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.bigsolutions.sophie',
  appName: 'SOPHIE ERP',
  webDir: 'dist',
  bundledWebRuntime: false,
  server: {
    cleartext: false,
    androidScheme: 'https',
  },
}

export default config
