import React, {useEffect, useState, useRef} from 'react';
import {StyleSheet, View, Text, ActivityIndicator, TouchableOpacity} from 'react-native';
import MapView, {Marker, Circle, PROVIDER_GOOGLE} from 'react-native-maps';
import {useIsFocused} from '@react-navigation/native';
import {LocationService} from '@services/LocationService';
import {ApiService} from '@services/ApiService';
import {MapsConfigService} from '@services/MapsConfigService';
import type {Hazard} from '../types';

export function MapScreen(): React.JSX.Element {
  const [hazards, setHazards] = useState<Hazard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [userLocation, setUserLocation] = useState<{latitude: number; longitude: number} | null>(null);
  const [hasApiKey, setHasApiKey] = useState(false);
  const [mapTilesLoaded, setMapTilesLoaded] = useState(false);
  const mapRef = useRef<MapView>(null);
  const isFocused = useIsFocused();
  const tilesLoadTimeout = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    initializeMap();

    // Set a timeout to force show map even if tiles don't load
    tilesLoadTimeout.current = setTimeout(() => {
      if (!mapTilesLoaded) {
        console.log('Map tiles did not load within 5 seconds, showing map anyway');
        setMapTilesLoaded(true);
      }
    }, 5000);

    const interval = setInterval(fetchHazards, 30000); // Refresh every 30s
    return () => {
      clearInterval(interval);
      if (tilesLoadTimeout.current) {
        clearTimeout(tilesLoadTimeout.current);
      }
    };
  }, []);

  // Re-check API key when screen comes into focus
  useEffect(() => {
    if (isFocused) {
      checkApiKey();
    }
  }, [isFocused]);

  const checkApiKey = async () => {
    try {
      const mapsConfigService = MapsConfigService.getInstance();
      mapsConfigService.clearCache(); // Clear cache to force reload
      const apiKey = await mapsConfigService.getApiKey();

      if (!apiKey || apiKey.trim() === '') {
        setHasApiKey(false);
      } else if (!hasApiKey) {
        // API key was just added, reinitialize
        setHasApiKey(true);
        setIsLoading(true);
        await initializeMap();
      }
    } catch (error) {
      console.error('Failed to check API key:', error);
    }
  };

  const initializeMap = async () => {
    try {
      console.log('Initializing map...');
      // Check if Google Maps API key is configured
      const mapsConfigService = MapsConfigService.getInstance();
      const apiKey = await mapsConfigService.getApiKey();
      console.log('API key check:', apiKey ? 'Found' : 'Not found');

      if (!apiKey || apiKey.trim() === '') {
        console.log('No API key, showing error screen');
        setHasApiKey(false);
        setIsLoading(false);
        return;
      }

      setHasApiKey(true);
      console.log('API key validated, getting location...');

      const locationService = LocationService.getInstance();

      // Try to get current location
      let location = locationService.getLastKnownLocation();

      if (!location) {
        try {
          // If no cached location, get current location
          console.log('No cached location, requesting current location...');
          location = await locationService.getCurrentLocation();
          console.log('Got current location:', location);
        } catch (error) {
          console.error('Failed to get current location:', error);
          // Use default location if can't get user location
          location = {
            latitude: 37.78825,
            longitude: -122.4324,
            accuracy: 0,
            altitude: null,
            speed: null,
            heading: null,
            timestamp: Date.now(),
          };
        }
      }

      console.log('Setting user location state:', location);
      setUserLocation({
        latitude: location.latitude,
        longitude: location.longitude,
      });

      console.log('Fetching hazards...');
      await fetchHazards(location);
      console.log('Map initialization complete, setting isLoading to false');
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to initialize map:', error);
      setIsLoading(false);
    }
  };

  const fetchHazards = async (providedLocation?: any) => {
    try {
      console.log('fetchHazards called, userLocation:', userLocation);
      const locationService = LocationService.getInstance();
      let location = providedLocation || locationService.getLastKnownLocation();
      console.log('Location to use:', location);

      // If no cached location, try to get current location
      if (!location && userLocation) {
        console.log('Using userLocation state as fallback');
        // Use the userLocation state if available
        location = {
          latitude: userLocation.latitude,
          longitude: userLocation.longitude,
          accuracy: 0,
          altitude: null,
          speed: null,
          heading: null,
          timestamp: Date.now(),
        };
      }

      if (!location) {
        console.log('No location available for fetching hazards');
        return;
      }

      console.log('Fetching hazards for location:', location.latitude, location.longitude);
      const apiService = ApiService.getInstance();
      const nearbyHazards = await apiService.getNearbyHazards(
        location.latitude,
        location.longitude,
        5000, // 5km radius
      );

      console.log(`Loaded ${nearbyHazards.length} hazards`);
      setHazards(nearbyHazards);
    } catch (error) {
      console.error('Failed to fetch hazards:', error);
      // Don't throw, just log the error so map can still load
    }
  };

  const centerOnUser = () => {
    if (userLocation && mapRef.current) {
      mapRef.current.animateToRegion({
        latitude: userLocation.latitude,
        longitude: userLocation.longitude,
        latitudeDelta: 0.01,
        longitudeDelta: 0.01,
      });
    }
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity.toLowerCase()) {
      case 'high':
        return '#FF3B30';
      case 'medium':
        return '#FF9500';
      case 'low':
        return '#FFCC00';
      default:
        return '#999999';
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading map...</Text>
      </View>
    );
  }

  if (!hasApiKey) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.errorTitle}>Google Maps API Key Required</Text>
        <Text style={styles.errorText}>
          Please configure your Google Maps API key in Settings to use the map feature.
        </Text>
        <Text style={styles.errorHint}>
          Go to Settings tab → Enter your Google Maps API key → Save
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        provider={PROVIDER_GOOGLE}
        style={styles.map}
        initialRegion={{
          latitude: userLocation?.latitude || 37.78825,
          longitude: userLocation?.longitude || -122.4324,
          latitudeDelta: 0.0922,
          longitudeDelta: 0.0421,
        }}
        showsUserLocation
        showsMyLocationButton={false}
        loadingEnabled
        onMapReady={() => {
          console.log('Map is ready!');
          setMapTilesLoaded(true);
          if (tilesLoadTimeout.current) {
            clearTimeout(tilesLoadTimeout.current);
          }
        }}
        onMapLoaded={() => {
          console.log('Map loaded successfully!');
          setMapTilesLoaded(true);
        }}>

        {hazards.map(hazard => (
          <React.Fragment key={hazard.id}>
            <Marker
              coordinate={{
                latitude: hazard.latitude,
                longitude: hazard.longitude,
              }}
              title={`Severity ${hazard.severity} Hazard`}
              description={`${hazard.detectionCount} detections • Confidence: ${(hazard.confidence * 100).toFixed(0)}%`}
              pinColor={getSeverityColor(hazard.severity.toString())}
            />
            <Circle
              center={{
                latitude: hazard.latitude,
                longitude: hazard.longitude,
              }}
              radius={15}
              fillColor={`${getSeverityColor(hazard.severity.toString())}30`}
              strokeColor={getSeverityColor(hazard.severity.toString())}
              strokeWidth={2}
            />
          </React.Fragment>
        ))}
      </MapView>

      <View style={styles.statsOverlay}>
        <Text style={styles.statsText}>{hazards.length} hazards nearby</Text>
        {!mapTilesLoaded && (
          <Text style={styles.loadingTilesText}>Loading map tiles...</Text>
        )}
      </View>

      <TouchableOpacity style={styles.centerButton} onPress={centerOnUser}>
        <Text style={styles.centerButtonText}>📍</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.refreshButton} onPress={fetchHazards}>
        <Text style={styles.refreshButtonText}>🔄</Text>
      </TouchableOpacity>

      <View style={styles.legendContainer}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, {backgroundColor: '#FF3B30'}]} />
          <Text style={styles.legendText}>High</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, {backgroundColor: '#FF9500'}]} />
          <Text style={styles.legendText}>Medium</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, {backgroundColor: '#FFCC00'}]} />
          <Text style={styles.legendText}>Low</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  loadingTilesText: {
    fontSize: 12,
    color: '#FF9500',
    marginTop: 5,
    textAlign: 'center',
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
    textAlign: 'center',
  },
  errorText: {
    fontSize: 16,
    color: '#666',
    marginBottom: 10,
    textAlign: 'center',
    paddingHorizontal: 30,
  },
  errorHint: {
    fontSize: 14,
    color: '#007AFF',
    textAlign: 'center',
    paddingHorizontal: 30,
    marginTop: 10,
  },
  statsOverlay: {
    position: 'absolute',
    top: 10,
    left: 10,
    right: 10,
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  statsText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    textAlign: 'center',
  },
  centerButton: {
    position: 'absolute',
    bottom: 100,
    right: 20,
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  centerButtonText: {
    fontSize: 24,
  },
  refreshButton: {
    position: 'absolute',
    bottom: 160,
    right: 20,
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  refreshButtonText: {
    fontSize: 24,
  },
  legendContainer: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 15,
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 6,
  },
  legendText: {
    fontSize: 12,
    color: '#333',
    fontWeight: '500',
  },
});
