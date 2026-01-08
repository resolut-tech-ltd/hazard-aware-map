module.exports = {
  presets: ['module:@react-native/babel-preset'],
  plugins: [
    [
      'module-resolver',
      {
        root: ['./src'],
        extensions: ['.ios.js', '.android.js', '.js', '.ts', '.tsx', '.json'],
        alias: {
          '@services': './src/services',
          '@storage': './src/storage',
          '@screens': './src/screens',
          '@utils': './src/utils',
          '@types': './src/types',
          '@components': './src/components',
        },
      },
    ],
  ],
};
