import AsyncStorage from '@react-native-async-storage/async-storage';
import {ApiService} from './ApiService';
import DeviceInfo from 'react-native-device-info';

const TOKEN_KEY = '@bump_aware_token';
const EMAIL_KEY = '@bump_aware_email';

export class AuthService {
  private static instance: AuthService;
  private token: string | null = null;
  private email: string | null = null;

  private constructor() {}

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  public async initialize(): Promise<boolean> {
    try {
      this.token = await AsyncStorage.getItem(TOKEN_KEY);
      this.email = await AsyncStorage.getItem(EMAIL_KEY);

      if (this.token) {
        const apiService = ApiService.getInstance();
        apiService.setAuthToken(this.token);
        return true;
      }

      return false;
    } catch (error) {
      console.error('Failed to initialize auth:', error);
      return false;
    }
  }

  public async register(email: string, password: string): Promise<void> {
    const apiService = ApiService.getInstance();
    const deviceId = await DeviceInfo.getUniqueId();

    const token = await apiService.register(email, password, deviceId);

    this.token = token;
    this.email = email;

    await AsyncStorage.setItem(TOKEN_KEY, token);
    await AsyncStorage.setItem(EMAIL_KEY, email);

    apiService.setAuthToken(token);
  }

  public async login(email: string, password: string): Promise<void> {
    const apiService = ApiService.getInstance();

    const token = await apiService.login(email, password);

    this.token = token;
    this.email = email;

    await AsyncStorage.setItem(TOKEN_KEY, token);
    await AsyncStorage.setItem(EMAIL_KEY, email);

    apiService.setAuthToken(token);
  }

  public async logout(): Promise<void> {
    this.token = null;
    this.email = null;

    await AsyncStorage.removeItem(TOKEN_KEY);
    await AsyncStorage.removeItem(EMAIL_KEY);

    const apiService = ApiService.getInstance();
    apiService.setAuthToken('');
  }

  public isAuthenticated(): boolean {
    return this.token !== null;
  }

  public getEmail(): string | null {
    return this.email;
  }

  public getToken(): string | null {
    return this.token;
  }
}
