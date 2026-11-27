import { Injectable, signal, computed } from '@angular/core';

export interface User {
  name: string;
  email: string;
}

@Injectable({ providedIn: 'root' })
export class Auth {
  private readonly _user = signal<User | null>(null);

  readonly user = this._user.asReadonly();
  readonly isLoggedIn = computed(() => this._user() !== null);

  // MOCKS : seront remplacés par des appels HttpClient vers le backend de l'équipe
  async login(email: string, password: string): Promise<boolean> {
    await new Promise(r => setTimeout(r, 600));
    if (email && password.length >= 6) {
      this._user.set({ name: 'Sarah', email });
      return true;
    }
    return false;
  }

  async register(name: string, email: string, password: string): Promise<boolean> {
    await new Promise(r => setTimeout(r, 600));
    this._user.set({ name, email });
    return true;
  }

  logout() {
    this._user.set(null);
  }
}