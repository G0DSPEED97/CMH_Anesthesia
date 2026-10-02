import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { AnesthesiaCase, Rank, Settings, User } from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/v1';

  login(username: string, password: string) { return this.http.post<User>(`${this.base}/auth/login`, { username, password }); }
  logout() { return this.http.post<void>(`${this.base}/auth/logout`, {}); }
  me() { return this.http.get<User>(`${this.base}/auth/me`); }
  changePassword(current_password: string, new_password: string) { return this.http.post<void>(`${this.base}/auth/password`, { current_password, new_password }); }
  ranks() { return this.http.get<Rank[]>(`${this.base}/ranks`); }
  settings() { return this.http.get<Settings>(`${this.base}/settings`); }
  saveSettings(value: Settings) { return this.http.put<Settings>(`${this.base}/settings`, value); }
  createCase(value: unknown) { return this.http.post<AnesthesiaCase>(`${this.base}/cases`, value); }
  cases(filters: Record<string, string> = {}) {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => { if (value) params = params.set(key, value); });
    return this.http.get<AnesthesiaCase[]>(`${this.base}/cases`, { params });
  }
  updateConsultation(id: string, value: unknown) { return this.http.patch<AnesthesiaCase>(`${this.base}/cases/${id}/consultation`, value); }
  updateOt(id: string, value: unknown) { return this.http.patch<AnesthesiaCase>(`${this.base}/cases/${id}/ot-status`, value); }
  printToken(id: string) { return this.http.post<{generated: boolean; queued: boolean; message: string}>(`${this.base}/cases/${id}/print-token`, {}); }
  receptionDisplay() { return this.http.get<{current: AnesthesiaCase | null; upcoming: AnesthesiaCase[]}>(`${this.base}/display/reception`); }
  otDisplay(day: string) { return this.http.get<{date: string; active: AnesthesiaCase[]; upcoming: AnesthesiaCase[]; completed_count: number; settings: Partial<Settings>}>(`${this.base}/display/ot`, { params: { for_date: day } }); }
}
