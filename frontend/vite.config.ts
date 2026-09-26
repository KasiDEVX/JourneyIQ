import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

function bundleAnalyzer(): Plugin {
  return {
    name: 'bundle-analyzer',
    generateBundle(_options, bundle) {
      const moduleSizes: { id: string; size: number }[] = []
      const packageSizes: Record<string, number> = {}

      for (const [, chunk] of Object.entries(bundle)) {
        if (chunk.type === 'chunk') {
          for (const [id, mod] of Object.entries(chunk.modules)) {
            moduleSizes.push({ id, size: mod.renderedLength })

            // Aggregate by package or src
            let pkgName = 'src'
            if (id.includes('node_modules')) {
              const match = id.replace(/\\/g, '/').match(/node_modules\/(?:@([^/]+)\/([^/]+)|([^/]+))/)
              if (match) {
                pkgName = match[1] && match[2] ? `@${match[1]}/${match[2]}` : match[3] || 'other'
              } else {
                pkgName = 'node_modules/other'
              }
            }
            packageSizes[pkgName] = (packageSizes[pkgName] || 0) + mod.renderedLength
          }
        }
      }

      moduleSizes.sort((a, b) => b.size - a.size)

      const topModules = moduleSizes.slice(0, 15).map(m => {
        const normalized = m.id.replace(/\\/g, '/')
        const shortId = normalized.includes('node_modules/')
          ? normalized.slice(normalized.indexOf('node_modules/'))
          : normalized.includes('src/')
          ? normalized.slice(normalized.indexOf('src/'))
          : normalized
        return { path: shortId, sizeBytes: m.size, sizeKB: (m.size / 1024).toFixed(2) + ' KB' }
      })

      const sortedPackages = Object.entries(packageSizes)
        .sort((a, b) => b[1] - a[1])
        .map(([pkg, size]) => ({
          package: pkg,
          sizeBytes: size,
          sizeKB: (size / 1024).toFixed(2) + ' KB',
        }))

      const report = {
        topModules,
        packages: sortedPackages,
      }

      fs.writeFileSync(
        path.resolve(__dirname, 'bundle-analysis.json'),
        JSON.stringify(report, null, 2),
      )
      console.log('\n====== BUNDLE ANALYSIS REPORT ======')
      console.log('\n--- TOP 10 MODULES BY RENDERED SIZE ---')
      topModules.slice(0, 10).forEach((m, i) => {
        console.log(`${i + 1}. [${m.sizeKB}] ${m.path}`)
      })
      console.log('\n--- TOP PACKAGES / FOLDERS ---')
      sortedPackages.slice(0, 10).forEach((p, i) => {
        console.log(`${i + 1}. [${p.sizeKB}] ${p.package}`)
      })
      console.log('====================================\n')
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), bundleAnalyzer()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom') || id.includes('node_modules/react-router')) {
            return 'vendor-react'
          }
          if (id.includes('node_modules/recharts') || id.includes('node_modules/d3-') || id.includes('node_modules/victory-vendor')) {
            return 'vendor-charts'
          }
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
