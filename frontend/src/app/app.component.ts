import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from './api.service';
import { AnesthesiaCase, Rank, Settings, User, View } from './models';

const today = () => new Date().toLocaleDateString('en-CA');

@Component({
  selector: 'cmh-root',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  user: User | null = null;
  view: View = 'reception';
  ranks: Rank[] = [];
  cases: AnesthesiaCase[] = [];
  receptionCurrent: AnesthesiaCase | null = null;
  receptionUpcoming: AnesthesiaCase[] = [];
  otActive: AnesthesiaCase[] = [];
  otUpcoming: AnesthesiaCase[] = [];
  completedCount = 0;
  settings: Settings = { token_prefix: 'A', token_paper_width_mm: 80, token_paper_height_mm: 110, token_printer_name: '', token_auto_print: false, form_printer_name: '', form_auto_print: false, barcode_format: 'code128', current_slide_seconds: 10, upcoming_slide_seconds: 15, ot_tables: ['OT-1', 'OT-2', 'OT-3'] };
  selectedCase: AnesthesiaCase | null = null;
  busy = false;
  message = '';
  error = '';
  loginForm = { username: '', password: '' };
  passwordForm = { current: '', next: '', confirm: '' };
  search = '';
  rankSearch = '';
  rankMenuOpen = false;
  rosterDate = today();
  displaySlide: 'current' | 'upcoming' = 'current';
  registerForm = { service_number: '', rank_code: '', name: '', unit: '', age: null as number | null, sex: 'male', proposed_surgery: '', proposed_anesthetic: 'GA', auto_print_token: true };
  consultForm = { status: 'completed', scheduled_ot_date: '', ward: '', disease: '', operation: '', surgeon: '', anesthesiologist: '', asa_class: 'I', ot_table: '', ot_serial: null as number | null };
  private ws: WebSocket | null = null;
  private displayTimer: number | null = null;
  private reconnectTimer: number | null = null;

  ngOnInit() {
    this.api.me().subscribe({ next: user => this.onAuthenticated(user), error: () => undefined });
  }

  ngOnDestroy() {
    this.ws?.close();
    if (this.displayTimer) window.clearTimeout(this.displayTimer);
    if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer);
  }

  login() {
    this.clearNotice(); this.busy = true;
    this.api.login(this.loginForm.username, this.loginForm.password).subscribe({
      next: user => { this.busy = false; this.loginForm.password = ''; this.onAuthenticated(user); },
      error: error => this.fail(error),
    });
  }

  changePassword() {
    this.clearNotice();
    if (this.passwordForm.next !== this.passwordForm.confirm) { this.error = 'New passwords do not match.'; return; }
    this.busy = true;
    this.api.changePassword(this.passwordForm.current, this.passwordForm.next).subscribe({
      next: () => { this.busy = false; this.message = 'Password changed successfully.'; if (this.user) this.user.must_change_password = false; this.bootstrap(); },
      error: error => this.fail(error),
    });
  }

  logout() { this.api.logout().subscribe(() => { this.user = null; this.ws?.close(); }); }

  can(view: View) {
    if (!this.user) return false;
    const allowed: Record<View, string[]> = {
      reception: ['admin', 'reception'], doctor: ['admin', 'doctor'], 'reception-display': ['admin', 'reception', 'doctor', 'display'],
      'ot-control': ['admin', 'ot_controller'], 'ot-display': ['admin', 'ot_controller', 'display'], settings: ['admin'],
    };
    return allowed[view].includes(this.user.role);
  }

  setView(view: View) {
    if (!this.can(view)) return;
    this.view = view; this.selectedCase = null; this.refresh();
    if (view.endsWith('display')) this.scheduleSlide();
  }

  submitRegistration() {
    this.clearNotice(); this.busy = true;
    const payload = {
      patient: { service_number: this.registerForm.service_number, rank_code: this.registerForm.rank_code, name: this.registerForm.name, unit: this.registerForm.unit, age: this.registerForm.age, sex: this.registerForm.sex },
      proposed_surgery: this.registerForm.proposed_surgery, proposed_anesthetic: this.registerForm.proposed_anesthetic, auto_print_token: this.registerForm.auto_print_token,
    };
    this.api.createCase(payload).subscribe({
      next: created => {
        this.busy = false; this.message = `${created.token_number} created. Token and anaesthesia form are ready.`;
        this.registerForm = { service_number: '', rank_code: '', name: '', unit: '', age: null, sex: 'male', proposed_surgery: '', proposed_anesthetic: 'GA', auto_print_token: true };
        this.rankSearch = '';
        this.refresh();
      },
      error: error => this.fail(error),
    });
  }

  get filteredRanks() {
    const query = this.rankSearch.trim().toLowerCase();
    return this.ranks
      .filter(rank => !query || `${rank.label} ${rank.category} ${rank.code}`.toLowerCase().includes(query))
      .slice(0, 12);
  }

  selectRank(rank: Rank) {
    this.registerForm.rank_code = rank.code;
    this.rankSearch = rank.label;
    this.rankMenuOpen = false;
  }

  selectCase(item: AnesthesiaCase) {
    this.selectedCase = item;
    this.consultForm = {
      status: item.consultation_status, scheduled_ot_date: item.scheduled_ot_date ?? '', ward: item.ward ?? '', disease: item.disease ?? '', operation: item.operation ?? item.proposed_surgery,
      surgeon: item.surgeon ?? '', anesthesiologist: item.anesthesiologist ?? '', asa_class: item.asa_class ?? 'I', ot_table: item.ot_table ?? '', ot_serial: item.ot_serial,
    };
  }

  saveConsultation() {
    if (!this.selectedCase) return;
    this.clearNotice(); this.busy = true;
    const payload = { ...this.consultForm, scheduled_ot_date: this.consultForm.scheduled_ot_date || null, ot_table: this.consultForm.ot_table || null, ot_serial: this.consultForm.ot_serial || null, expected_version: this.selectedCase.version };
    this.api.updateConsultation(this.selectedCase.id, payload).subscribe({ next: item => { this.busy = false; this.selectedCase = item; this.message = 'Doctor review and OT schedule saved.'; this.refresh(); }, error: error => this.fail(error) });
  }

  quickConsultStatus(item: AnesthesiaCase, status: string) {
    this.api.updateConsultation(item.id, { status, expected_version: item.version }).subscribe({ next: () => this.refresh(), error: error => this.fail(error) });
  }

  setOtStatus(item: AnesthesiaCase, status: string) {
    this.clearNotice();
    this.api.updateOt(item.id, { status, status_note: item.status_note, ot_table: item.ot_table, expected_version: item.version }).subscribe({ next: () => this.refresh(), error: error => this.fail(error) });
  }

  reprint(item: AnesthesiaCase) { this.api.printToken(item.id).subscribe({ next: result => this.message = result.message, error: error => this.fail(error) }); }
  tokenUrl(item: AnesthesiaCase) { return `/api/v1/cases/${item.id}/token.pdf`; }
  formUrl(item: AnesthesiaCase) { return `/api/v1/cases/${item.id}/form.pdf`; }

  saveSettings() {
    this.clearNotice(); this.busy = true;
    this.settings.ot_tables = this.settings.ot_tables.map(value => value.trim()).filter(Boolean);
    this.api.saveSettings(this.settings).subscribe({ next: value => { this.settings = value; this.busy = false; this.message = 'Settings saved.'; }, error: error => this.fail(error) });
  }

  trackCase(_: number, item: AnesthesiaCase) { return item.id; }

  private onAuthenticated(user: User) {
    this.user = user;
    if (!user.must_change_password) this.bootstrap();
  }

  private bootstrap() {
    this.api.ranks().subscribe(value => this.ranks = value);
    this.api.settings().subscribe(value => this.settings = value);
    const preferred: View = this.user?.role === 'doctor' ? 'doctor' : this.user?.role === 'ot_controller' ? 'ot-control' : this.user?.role === 'display' ? 'ot-display' : 'reception';
    this.view = preferred; this.refresh(); this.connectRealtime();
  }

  refresh() {
    if (!this.user) return;
    if (this.view === 'reception' || this.view === 'doctor') this.api.cases(this.search ? { q: this.search } : {}).subscribe(value => this.cases = value);
    if (this.view === 'ot-control') this.api.cases({ scheduled_ot_date: this.rosterDate }).subscribe(value => this.cases = value.sort((a, b) => (a.ot_serial ?? 999) - (b.ot_serial ?? 999)));
    if (this.view === 'reception-display') this.api.receptionDisplay().subscribe(value => { this.receptionCurrent = value.current; this.receptionUpcoming = value.upcoming; });
    if (this.view === 'ot-display') this.api.otDisplay(this.rosterDate).subscribe(value => { this.otActive = value.active; this.otUpcoming = value.upcoming; this.completedCount = value.completed_count; this.scheduleSlide(); });
  }

  private connectRealtime() {
    this.ws?.close();
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${scheme}://${location.host}/api/v1/ws`);
    this.ws.onmessage = () => this.refresh();
    this.ws.onclose = () => { this.reconnectTimer = window.setTimeout(() => this.connectRealtime(), 5000); };
  }

  private scheduleSlide() {
    if (this.displayTimer) window.clearTimeout(this.displayTimer);
    const seconds = this.displaySlide === 'current' ? this.settings.current_slide_seconds : this.settings.upcoming_slide_seconds;
    this.displayTimer = window.setTimeout(() => { this.displaySlide = this.displaySlide === 'current' ? 'upcoming' : 'current'; this.scheduleSlide(); }, seconds * 1000);
  }

  private clearNotice() { this.message = ''; this.error = ''; }
  private fail(error: HttpErrorResponse) { this.busy = false; this.error = error.error?.detail ?? 'The request could not be completed.'; }
}
