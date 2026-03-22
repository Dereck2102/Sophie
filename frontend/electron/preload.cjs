const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('sophieDesktop', {
  platform: process.platform,
  mode: 'electron',
})
