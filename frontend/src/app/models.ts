export type Role = 'admin' | 'reception' | 'doctor' | 'ot_controller' | 'auditor' | 'display';
export type View = 'reception' | 'doctor' | 'reception-display' | 'ot-control' | 'ot-display' | 'settings';

export interface User {
  id: string;
  username: string;
  display_name: string;
  role: Role;
  must_change_password: boolean;
}

export interface Rank { code: string; label: string; category: string; sort_order: number; }

export interface Patient {
  id: string;
  service_number: string;
  rank_code: string;
  rank_label: string;
  name: string;
  unit: string;
  age: number;
  sex: string;
}

export interface AnesthesiaCase {
  id: string;
  patient: Patient;
  token_date: string;
  token_number: string;
  proposed_surgery: string;
  proposed_anesthetic: string;
  consultation_status: string;
  scheduled_ot_date: string | null;
  ot_serial: number | null;
  ot_table: string | null;
  ward: string | null;
  disease: string | null;
  operation: string | null;
  surgeon: string | null;
  anesthesiologist: string | null;
  asa_class: string | null;
  ot_status: string;
  status_note: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Settings {
  token_prefix: string;
  token_paper_width_mm: number;
  token_paper_height_mm: number;
  token_printer_name: string;
  token_auto_print: boolean;
  form_printer_name: string;
  form_auto_print: boolean;
  barcode_format: 'code128';
  current_slide_seconds: number;
  upcoming_slide_seconds: number;
  ot_tables: string[];
}
