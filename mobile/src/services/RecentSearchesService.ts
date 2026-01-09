import AsyncStorage from '@react-native-async-storage/async-storage';

export interface RecentSearch {
  id: string;
  name: string;
  description: string;
  latitude: number;
  longitude: number;
  timestamp: number;
}

const STORAGE_KEY = '@bump_aware:recent_searches';
const MAX_RECENT_SEARCHES = 10;

export class RecentSearchesService {
  private static instance: RecentSearchesService;

  private constructor() {}

  public static getInstance(): RecentSearchesService {
    if (!RecentSearchesService.instance) {
      RecentSearchesService.instance = new RecentSearchesService();
    }
    return RecentSearchesService.instance;
  }

  /**
   * Get all recent searches, sorted by most recent first
   */
  async getRecentSearches(): Promise<RecentSearch[]> {
    try {
      const data = await AsyncStorage.getItem(STORAGE_KEY);
      if (!data) {
        return [];
      }
      const searches: RecentSearch[] = JSON.parse(data);
      return searches.sort((a, b) => b.timestamp - a.timestamp);
    } catch (error) {
      console.error('Failed to get recent searches:', error);
      return [];
    }
  }

  /**
   * Add a new search to recent searches
   * If the location already exists (within 50m), update it instead of duplicating
   */
  async addRecentSearch(
    name: string,
    description: string,
    latitude: number,
    longitude: number,
  ): Promise<void> {
    try {
      const searches = await this.getRecentSearches();

      // Check if this location already exists (within 50 meters)
      const existingIndex = searches.findIndex(search => {
        const distance = this.calculateDistance(
          search.latitude,
          search.longitude,
          latitude,
          longitude,
        );
        return distance < 50; // 50 meters threshold
      });

      // Remove existing entry if found
      if (existingIndex !== -1) {
        searches.splice(existingIndex, 1);
      }

      // Add new search at the beginning
      const newSearch: RecentSearch = {
        id: `${Date.now()}_${latitude}_${longitude}`,
        name,
        description,
        latitude,
        longitude,
        timestamp: Date.now(),
      };

      searches.unshift(newSearch);

      // Keep only the most recent searches
      const trimmedSearches = searches.slice(0, MAX_RECENT_SEARCHES);

      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(trimmedSearches));
    } catch (error) {
      console.error('Failed to add recent search:', error);
    }
  }

  /**
   * Clear all recent searches
   */
  async clearRecentSearches(): Promise<void> {
    try {
      await AsyncStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error('Failed to clear recent searches:', error);
    }
  }

  /**
   * Remove a specific recent search by ID
   */
  async removeRecentSearch(id: string): Promise<void> {
    try {
      const searches = await this.getRecentSearches();
      const filtered = searches.filter(search => search.id !== id);
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
    } catch (error) {
      console.error('Failed to remove recent search:', error);
    }
  }

  /**
   * Calculate distance between two coordinates using Haversine formula
   * Returns distance in meters
   */
  private calculateDistance(
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number,
  ): number {
    const R = 6371000; // Earth's radius in meters
    const dLat = this.toRad(lat2 - lat1);
    const dLon = this.toRad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRad(lat1)) *
        Math.cos(this.toRad(lat2)) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  private toRad(degrees: number): number {
    return degrees * (Math.PI / 180);
  }
}
