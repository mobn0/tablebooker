import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  NaAlert, NaBadge, NaButton, NaCard, NaDatepicker, NaEmptyState, NaField, NaInput,
  NaMessage, NaModal, NaPopconfirm, NaRow, NaSelect, NaSelectOption, NaStack,
} from 'newang';
import {
  Api, DiningTable, Guest, Reservation, Restaurant, STATUS_LABEL, STATUS_TONE, errorMessage, hhmm,
} from '../api';

const today = () => new Date().toISOString().slice(0, 10);

@Component({
  selector: 'app-reservations',
  imports: [
    FormsModule, NaAlert, NaBadge, NaButton, NaCard, NaDatepicker, NaEmptyState, NaField, NaInput,
    NaModal, NaPopconfirm, NaRow, NaSelect, NaStack,
  ],
  template: `
    <na-stack gap="lg">
      <na-row gap="md" align="end">
        <na-datepicker label="Day" [(value)]="day" (valueChange)="load()" />
        <na-field label="Restaurant">
          <na-select [options]="restaurantFilterOptions()" [(value)]="filterRestaurant" (valueChange)="load()" />
        </na-field>
        <na-button (pressed)="openNew()">New reservation</na-button>
      </na-row>

      @if (error()) { <na-alert tone="danger" showIcon closable (closed)="error.set('')">{{ error() }}</na-alert> }

      @if (reservations().length === 0) {
        <na-empty-state title="No reservations" description="Nothing booked for this day yet." />
      }
      @for (r of reservations(); track r.id) {
        <na-card [title]="hhmm(r.start_time) + ' · ' + r.guest_name"
                 [subtitle]="'Table ' + r.table_number + ' · ' + r.party_size + ' guests · ' + r.duration_minutes + ' min'">
          <na-row gap="sm" align="center">
            <na-badge [tone]="tone[r.status]">{{ label[r.status] }}</na-badge>
            @if (r.status === 'booked') {
              <na-button size="sm" variant="secondary" (pressed)="setStatus(r, 'complete')">Complete</na-button>
              <na-button size="sm" variant="secondary" (pressed)="setStatus(r, 'no-show')">No-show</na-button>
              <na-popconfirm message="Cancel this reservation?" (confirmed)="setStatus(r, 'cancel')">
                <na-button size="sm" variant="danger">Cancel</na-button>
              </na-popconfirm>
            }
          </na-row>
        </na-card>
      }
    </na-stack>

    <na-modal title="New reservation" [open]="modalOpen()" (closed)="modalOpen.set(false)">
      <na-stack gap="md">
        @if (formError()) { <na-alert tone="danger" showIcon>{{ formError() }}</na-alert> }
        <na-field label="Guest" required>
          <na-select [options]="guestOptions()" [(value)]="guestId" placeholder="Choose a guest" />
        </na-field>
        <na-field label="Restaurant" required>
          <na-select [options]="restaurantOptions()" [(value)]="restaurantId" (valueChange)="loadTables()" placeholder="Choose a restaurant" />
        </na-field>
        <na-datepicker label="Date" [(value)]="formDate" [min]="todayStr" required />
        <na-field label="Start time" required>
          <input naInput type="time" [(ngModel)]="startTime" />
        </na-field>
        <na-field label="Party size" required>
          <input naInput type="number" min="1" max="30" [(ngModel)]="partySize" />
        </na-field>
        <na-field label="Duration (minutes)" hint="Standard reservation: 90 minutes">
          <input naInput type="number" min="15" step="15" [(ngModel)]="duration" />
        </na-field>
        <na-field label="Table" hint="Automatic picks the best-fitting free table">
          <na-select [options]="tableOptions()" [(value)]="tableId" />
        </na-field>
        <na-row gap="sm" justify="end">
          <na-button variant="ghost" (pressed)="modalOpen.set(false)">Close</na-button>
          <na-button [loading]="saving()" (pressed)="submit()">Book</na-button>
        </na-row>
      </na-stack>
    </na-modal>
  `,
})
export class ReservationsPage implements OnInit {
  private api = inject(Api);
  private messages = inject(NaMessage);

  readonly tone = STATUS_TONE;
  readonly label = STATUS_LABEL;
  readonly hhmm = hhmm;
  readonly todayStr = today();

  day = signal(today());
  filterRestaurant = signal<string | number | undefined>(0);
  reservations = signal<Reservation[]>([]);
  restaurants = signal<Restaurant[]>([]);
  guests = signal<Guest[]>([]);
  tables = signal<DiningTable[]>([]);
  error = signal('');

  modalOpen = signal(false);
  formError = signal('');
  saving = signal(false);
  guestId = signal<string | number | undefined>(undefined);
  restaurantId = signal<string | number | undefined>(undefined);
  tableId = signal<string | number | undefined>(0);
  formDate = signal(today());
  startTime = '19:00';
  partySize = 2;
  duration = 90;

  restaurantFilterOptions = computed<NaSelectOption[]>(() => [
    { value: 0, label: 'All restaurants' },
    ...this.restaurants().map((r) => ({ value: r.id, label: r.name })),
  ]);
  restaurantOptions = computed<NaSelectOption[]>(() =>
    this.restaurants().map((r) => ({ value: r.id, label: r.name })),
  );
  guestOptions = computed<NaSelectOption[]>(() =>
    this.guests().map((g) => ({ value: g.id, label: `${g.first_name} ${g.last_name}` })),
  );
  tableOptions = computed<NaSelectOption[]>(() => [
    { value: 0, label: 'Automatic (best fit)' },
    ...this.tables().map((t) => ({ value: t.id, label: `Table ${t.number} · ${t.seats} seats · ${t.location}` })),
  ]);

  async ngOnInit() {
    this.restaurants.set(await this.api.restaurants());
    await this.load();
  }

  async load() {
    try {
      const rid = Number(this.filterRestaurant()) || undefined;
      this.reservations.set(await this.api.reservationsForDay(this.day(), rid));
    } catch (e) {
      this.error.set(errorMessage(e));
    }
  }

  async openNew() {
    this.formError.set('');
    // refresh lists: guests/restaurants may have changed in the other tabs
    const [guests, restaurants] = await Promise.all([this.api.guests(), this.api.restaurants()]);
    this.guests.set(guests);
    this.restaurants.set(restaurants);
    if (!this.restaurantId() && restaurants.length) this.restaurantId.set(restaurants[0].id);
    this.formDate.set(this.day() < this.todayStr ? this.todayStr : this.day());
    await this.loadTables();
    this.modalOpen.set(true);
  }

  async loadTables() {
    const id = Number(this.restaurantId());
    this.tableId.set(0);
    this.tables.set(id ? await this.api.tables(id) : []);
  }

  async submit() {
    this.formError.set('');
    if (!this.guestId() || !this.restaurantId()) {
      this.formError.set('Please choose a guest and a restaurant');
      return;
    }
    this.saving.set(true);
    try {
      await this.api.reserve({
        guest_id: Number(this.guestId()),
        restaurant_id: Number(this.restaurantId()),
        date: this.formDate(),
        start_time: this.startTime.length === 5 ? this.startTime + ':00' : this.startTime,
        party_size: Number(this.partySize),
        duration_minutes: Number(this.duration),
        table_id: Number(this.tableId()) || null,
      });
      this.messages.success('Reservation booked');
      this.modalOpen.set(false);
      this.day.set(this.formDate());
      await this.load();
    } catch (e) {
      this.formError.set(errorMessage(e));
    } finally {
      this.saving.set(false);
    }
  }

  async setStatus(r: Reservation, action: 'cancel' | 'complete' | 'no-show') {
    try {
      await this.api.setStatus(r.id, action);
      await this.load();
    } catch (e) {
      this.error.set(errorMessage(e));
    }
  }
}
