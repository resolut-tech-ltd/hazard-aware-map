# Bump Aware Mobile App

React Native mobile application for crowd-sourced road hazard detection using sensor fusion and GPS.

## Features

- **Background Sensor Monitoring**: Tri-axial accelerometer + gyroscope at 100-200Hz
- **High-Precision GPS**: Location tagging with <10m accuracy requirement
- **Local Storage**: SQLite database with optimized battery usage
- **Sensor Fusion**: Combined accelerometer and gyroscope data for improved accuracy
- **Batched Sync**: Efficient data upload to minimize battery drain
- **Real-time Statistics**: Detection counts, sync status, and monitoring state

## Technology Stack

- **Framework**: React Native 0.73
- **Language**: TypeScript
- **Sensors**: react-native-sensors (accelerometer, gyroscope)
- **Location**: react-native-geolocation-service
- **Storage**: react-native-sqlite-storage
- **Background Tasks**: react-native-background-actions
- **Maps**: react-native-maps
- **HTTP Client**: axios

## Prerequisites

### General Requirements
- Node.js 18+ and npm/yarn
- Git

### Android Development
- Android Studio (latest version)
- Android SDK 26+ (Android 8.0+)
- Java Development Kit (JDK) 17
- Android device or emulator with:
  - GPS capability
  - Accelerometer and gyroscope sensors
  - Android 8.0+ (API level 26+)

### iOS Development (Future)
- macOS with Xcode 14+
- CocoaPods
- iOS Simulator or physical device with iOS 12+

## Installation

### 1. Clone and Install Dependencies

```bash
cd mobile
npm install
# or
yarn install
```

### 2. Android Setup

#### Configure Android SDK

Ensure your `ANDROID_HOME` environment variable is set:

```bash
export ANDROID_HOME=$HOME/Library/Android/sdk  # macOS
# or
export ANDROID_HOME=$HOME/Android/Sdk  # Linux
# or
set ANDROID_HOME=C:\Users\YourUsername\AppData\Local\Android\Sdk  # Windows
```

Add platform-tools to PATH:

```bash
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
```

#### Install Android Permissions

The app requires the following permissions (auto-configured in `AndroidManifest.xml`):

- `ACCESS_FINE_LOCATION` - GPS tracking
- `ACCESS_COARSE_LOCATION` - Network-based location
- `ACCESS_BACKGROUND_LOCATION` - Background monitoring (Android 10+)
- `WAKE_LOCK` - Keep sensors active in background
- `FOREGROUND_SERVICE` - Background service
- `INTERNET` - API communication

### 3. iOS Setup (Future Support)

```bash
cd ios
pod install
cd ..
```

## Running the App

### Development Mode

#### Android

```bash
# Start Metro bundler
npm start

# In a new terminal, run on Android
npm run android
# or
npx react-native run-android
```

#### iOS (Future)

```bash
npm run ios
# or
npx react-native run-ios
```

### Production Build

#### Android

```bash
cd android
./gradlew assembleRelease

# APK will be at: android/app/build/outputs/apk/release/app-release.apk
```

## Project Structure

```
mobile/
├── src/
│   ├── services/           # Core services
│   │   ├── SensorService.ts       # Accelerometer & gyroscope monitoring
│   │   ├── LocationService.ts     # GPS tracking
│   │   └── ApiService.ts          # Backend communication
│   ├── storage/
│   │   └── Database.ts            # SQLite database layer
│   ├── screens/            # UI screens (future)
│   ├── components/         # Reusable components (future)
│   ├── utils/              # Utilities (future)
│   ├── types/
│   │   └── index.ts              # TypeScript interfaces
│   └── App.tsx             # Main application component
├── android/                # Android native code
├── ios/                    # iOS native code (future)
├── package.json
├── tsconfig.json
└── README.md
```

## Architecture

### Sensor Service (`SensorService.ts`)

Manages accelerometer and gyroscope data collection:

- Configurable sampling rate (100-200Hz)
- Real-time bump detection algorithm
- Magnitude calculation with gravity compensation
- Observable pattern for detection events

**Detection Algorithm**:
```
magnitude = sqrt(x² + y² + z²) - 9.8m/s²
threshold = 1.5g (configurable)

if magnitude > threshold:
  trigger detection event
```

### Location Service (`LocationService.ts`)

Handles GPS tracking:

- Continuous location tracking (5m distance filter)
- High accuracy mode (<10m requirement)
- Permission management
- Haversine distance calculation

### Database (`Database.ts`)

Local SQLite storage:

- Indexed tables for fast queries
- Batched inserts for efficiency
- Upload status tracking
- Statistics aggregation
- Automatic cleanup of old data (30 days)

### API Service (`ApiService.ts`)

Backend communication:

- RESTful API client
- JWT authentication
- Batched detection uploads
- Nearby hazard queries
- Automatic retry logic

## Configuration

### Environment Variables

Create a `.env` file in the mobile directory:

```env
API_BASE_URL=http://localhost:8080/api/v1
API_TIMEOUT=30000
SENSOR_SAMPLING_RATE=100
DETECTION_THRESHOLD=1.5
SYNC_INTERVAL=300000
```

### Sensor Tuning

Adjust detection sensitivity in `SensorService.ts`:

```typescript
const BUMP_THRESHOLD = 1.5; // Default: 1.5g

// Sensitivity levels:
// Low:    2.0g (only severe bumps)
// Medium: 1.5g (balanced)
// High:   1.0g (all bumps, may include false positives)
```

## Battery Optimization

The app implements several battery-saving strategies:

1. **Adaptive Sampling**: Sensors only active when moving
2. **Batched Uploads**: Group detections to minimize network usage
3. **Geofencing**: Reduce processing in inactive areas (future)
4. **Efficient Queries**: Indexed database operations
5. **Background Throttling**: Lower sampling rate when in background

**Expected Battery Usage**: <5% per hour of active monitoring

## Testing

### Unit Tests

```bash
npm test
# or
yarn test
```

### Manual Testing Checklist

- [ ] Sensor data collection at 100Hz+
- [ ] GPS accuracy <10m in open areas
- [ ] Bump detection on speed bumps
- [ ] Pothole detection
- [ ] Background operation
- [ ] Data persistence across app restarts
- [ ] Successful upload to backend
- [ ] Statistics accuracy
- [ ] Battery usage within targets

### Field Testing

1. Drive on roads with known bumps/potholes
2. Monitor detection rate and accuracy
3. Verify GPS precision (<10m)
4. Check battery drain over 1-hour session
5. Confirm successful background operation

## Troubleshooting

### Sensors Not Working

```bash
# Check if device has required sensors
adb shell
dumpsys sensorservice
```

### GPS Accuracy Issues

- Ensure location permissions granted
- Test in open area (not indoors)
- Wait 30-60 seconds for GPS lock
- Check `Settings > Location > Mode` is set to "High accuracy"

### Database Errors

```bash
# Clear app data
adb shell pm clear com.bumpaware

# Check database integrity
adb shell
cd /data/data/com.bumpaware/databases/
sqlite3 bump_aware.db
.schema
```

### Build Errors

```bash
# Clean build cache
cd android
./gradlew clean
cd ..

# Reset Metro bundler
npm start -- --reset-cache
```

## Performance Targets

- **Sensor Sampling Rate**: 100-200Hz
- **GPS Accuracy**: <10m (95% of readings)
- **Detection Latency**: <100ms from event to storage
- **Upload Latency**: <5s for batch of 50 detections
- **Battery Impact**: <5% per hour
- **App Size**: <50MB installed

## Future Enhancements

- [ ] iOS support
- [ ] Real-time hazard alerts on map
- [ ] Vehicle type configuration (SUV, sedan, motorcycle)
- [ ] Manual hazard reporting
- [ ] Offline map support
- [ ] Social features (leaderboards, badges)
- [ ] Machine learning for improved detection
- [ ] Integration with navigation apps

## Contributing

1. Follow TypeScript best practices
2. Maintain test coverage >80%
3. Document all public APIs
4. Use conventional commit messages
5. Test on physical devices before PR

## License

[To be determined]

## Support

For issues or questions:
- Open a GitHub issue
- Check existing documentation
- Review troubleshooting guide above
