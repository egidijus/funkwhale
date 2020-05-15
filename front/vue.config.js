const baseUrl = process.env.BASE_URL || '/front/'

const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
const webpack = require('webpack');
const PurgecssPlugin = require('purgecss-webpack-plugin')
const PreloadWebpackPlugin = require('preload-webpack-plugin');
const glob = require('glob-all')
const path = require('path')
let plugins = [
  // do not include moment.js locales since it's quite heavy
  new webpack.IgnorePlugin(/^\.\/locale$/, /moment$/),
  new PreloadWebpackPlugin({
    rel: 'preload',
    include: ['audio', 'core', 'about']
  }),
]
if (process.env.BUNDLE_ANALYZE === '1') {
  plugins.push(new BundleAnalyzerPlugin())
}
// Disabled because it causes some issues, like #1032, since some useful rules are still
// removed, and we cannot detect this during development
// plugins.push(
//   new PurgecssPlugin({
//     paths: glob.sync([
//       path.join(__dirname, './public/index.html'),
//       path.join(__dirname, './public/embed.html'),
//       path.join(__dirname, './**/*.vue'),
//       path.join(__dirname, './src/**/*.js')
//     ]),
//     whitelist: ['scale'],
//     whitelistPatterns: [/plyr/, /toast/, /transition/, /visible/],
//     whitelistPatternsChildren: [/plyr/, /dropdown/, /upward/]
//   }),
// )
module.exports = {
  publicPath: baseUrl,
  productionSourceMap: false,
  // Add settings for manifest file
  pwa: {
    name: 'Funkwhale',
    themeColor: '#f2711c',
    msTileColor: '#000000',
    appleMobileWebAppCapable: 'yes',
    appleMobileWebAppStatusBarStyle: 'black',
    workboxPluginMode: 'InjectManifest',
    manifestOptions: {
      display: 'minimal-ui',
      start_url: '.',
      description: 'A social platform to enjoy and share music',
      scope: "/",
      categories: ["music"],
      icons: [
        {
          'src': baseUrl + 'favicon.png',
          'sizes': '192x192',
          'type': 'image/png'
        },        {
          'src': baseUrl + 'favicon.png',
          'sizes': '512x512',
          'type': 'image/png'
        },
      ]
    },
    workboxOptions: {
      importWorkboxFrom: 'local',
      // swSrc is required in InjectManifest mode.
      swSrc: 'src/service-worker.js',
      swDest: 'service-worker.js',
      exclude: [
        new RegExp('js/locale.*'),
        new RegExp('js/moment-locale.*'),
        new RegExp('js/admin.*'),
        new RegExp('css/admin.*'),
      ]
    },
    iconPaths: {
      favicon32: 'favicon.png',
      favicon16: 'favicon.png',
      appleTouchIcon: 'favicon.png',
      maskIcon: 'favicon.png',
      msTileImage: 'favicon.png'
    }
  },
  pages: {
    embed: {
      entry: 'src/embed.js',
      template: 'public/embed.html',
      filename: 'embed.html',
      chunks: ['chunk-vendors', 'chunk-common', 'chunk-embed-vendors', 'embed']
    },
    index: {
      entry: 'src/main.js',
      template: 'public/index.html',
      filename: 'index.html',
      chunks: ['chunk-vendors', 'chunk-common', 'chunk-index-vendors', 'index']
    }
  },
  chainWebpack: config => {
    // config.plugins.delete('prefetch-embed')
    // config.plugins.delete('preload-embed')
    // config.plugins.delete('prefetch-index')
    // TODO: Remove this workaround once https://github.com/vuejs/vue-cli/issues/2463 is fixed
    // Remove preload plugins for multi-page build to prevent infinite recursion
    ['embed', 'index'].forEach(page => {
      config.plugins.delete(`preload-${page}`)
      config.plugins.delete(`prefetch-${page}`)
    })
    // needed to avoid having big dependedncies included in our lightweight
    // embed.html, cf https://github.com/vuejs/vue-cli/issues/2381
    const options = module.exports
    const pages = options.pages
    const pageKeys = Object.keys(pages)

    // Long-term caching

    const IS_VENDOR = /[\\/]node_modules[\\/]/

    config.optimization
      .splitChunks({
        cacheGroups: {
          vendors: {
            name: 'chunk-vendors',
            priority: -10,
            chunks: 'initial',
            minChunks: 2,
            test: IS_VENDOR,
            enforce: true,
          },
          ...pageKeys.map(key => ({
            name: `chunk-${key}-vendors`,
            priority: -11,
            chunks: chunk => chunk.name === key,
            test: IS_VENDOR,
            enforce: true,
          })),
          common: {
            name: 'chunk-common',
            priority: -20,
            chunks: 'initial',
            minChunks: 2,
            reuseExistingChunk: true,
            enforce: true,
          },
        },
      })
  },
  configureWebpack: {
    plugins: plugins,
    devtool: false
  },
  devServer: {
    disableHostCheck: true,
    // use https://node1.funkwhale.test/front-server/ if you use docker with federation
    public: process.env.FRONT_DEVSERVER_URL || ('http://localhost:' + (process.env.VUE_PORT || '8080'))
  },
  css: {
    loaderOptions: {
      sass: {
        implementation: require('sass')
      }
    }
  }
}
