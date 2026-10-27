import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface Restaurant {
  id: number;
  name: string;
  address: string;
  opening_time: string;
  closing_time: string;
}
export interface DiningTable {
  id: number;
  restaurant_id: number;
  number: number;
  seats: number;
  location: string;
}
export interface Guest {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
}
export type ReservationStatus = 'booked' | 'cancelled' | 'completed' | 'no_show';
export interface Reservation {
  id: number;
  guest_id: number;
  table_id: number;
  date: string;
  start_time: string;
  duration_minutes: number;
  party_size: number;
  status: ReservationStatus;
  guest_name: string;
  table_number: number;
  restaurant_id: number;
}
export interface NewReservation {
  guest_id: number;
  restaurant_id: number;
  date: string;
  start_time: string;
  party_size: number;
  duration_minutes: number;
  table_id: number | null;
}

/** Extracts a readable message from a FastAPI error response. */
export function errorMessage(e: unknown): string {
  if (e instanceof HttpErrorResponse) {
    const d = e.error?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map((x) => x.msg).join(', ');
    return e.message;
  }
  return 'Unexpected error';
}

@Injectable({ providedIn: 'root' })
export class Api {
  private http = inject(HttpClient);
  private base = '/api';

  restaurants = () => firstValueFrom(this.http.get<Restaurant[]>(`${this.base}/restaurants`));
  saveRestaurant = (r: Omit<Restaurant, 'id'>, id?: number) =>
    firstValueFrom(
      id
        ? this.http.put<Restaurant>(`${this.base}/restaurants/${id}`, r)
        : this.http.post<Restaurant>(`${this.base}/restaurants`, r),
    );
  deleteRestaurant = (id: number) => firstValueFrom(this.http.delete(`${this.base}/restaurants/${id}`));

  tables = (restaurantId: number) =>
    firstValueFrom(this.http.get<DiningTable[]>(`${this.base}/tables`, { params: { restaurant_id: restaurantId } }));
  saveTable = (t: Omit<DiningTable, 'id'>, id?: number) =>
    firstValueFrom(
      id
        ? this.http.put<DiningTable>(`${this.base}/tables/${id}`, t)
        : this.http.post<DiningTable>(`${this.base}/tables`, t),
    );
  deleteTable = (id: number) => firstValueFrom(this.http.delete(`${this.base}/tables/${id}`));

  guests = () => firstValueFrom(this.http.get<Guest[]>(`${this.base}/guests`));
  saveGuest = (g: Omit<Guest, 'id'>, id?: number) =>
    firstValueFrom(
      id
        ? this.http.put<Guest>(`${this.base}/guests/${id}`, g)
        : this.http.post<Guest>(`${this.base}/guests`, g),
    );
  deleteGuest = (id: number) => firstValueFrom(this.http.delete(`${this.base}/guests/${id}`));

  reservationsForDay = (day: string, restaurantId?: number) =>
    firstValueFrom(
      this.http.get<Reservation[]>(`${this.base}/reservations`, {
        params: restaurantId ? { day, restaurant_id: restaurantId } : { day },
      }),
    );
  guestHistory = (guestId: number) =>
    firstValueFrom(this.http.get<Reservation[]>(`${this.base}/reservations/by-guest/${guestId}`));
  reserve = (r: NewReservation) => firstValueFrom(this.http.post<Reservation>(`${this.base}/reservations`, r));
  setStatus = (id: number, action: 'cancel' | 'complete' | 'no-show') =>
    firstValueFrom(this.http.post<Reservation>(`${this.base}/reservations/${id}/${action}`, {}));
}

export const STATUS_TONE: Record<ReservationStatus, 'lime' | 'success' | 'neutral' | 'danger'> = {
  booked: 'lime',
  completed: 'success',
  cancelled: 'neutral',
  no_show: 'danger',
};
export const STATUS_LABEL: Record<ReservationStatus, string> = {
  booked: 'Booked',
  completed: 'Completed',
  cancelled: 'Cancelled',
  no_show: 'No-show',
};
export const hhmm = (t: string) => t.slice(0, 5);
