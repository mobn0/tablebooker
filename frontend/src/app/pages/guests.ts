import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  NaAlert, NaBadge, NaButton, NaCard, NaEmptyState, NaField, NaHeading, NaInput, NaMessage,
  NaModal, NaPopconfirm, NaRow, NaStack, NaText,
} from 'newang';
import { Api, Guest, Reservation, STATUS_LABEL, STATUS_TONE, errorMessage, hhmm } from '../api';

@Component({
  selector: 'app-guests',
  imports: [
    FormsModule, NaAlert, NaBadge, NaButton, NaCard, NaEmptyState, NaField, NaHeading, NaInput,
    NaModal, NaPopconfirm, NaRow, NaStack, NaText,
  ],
  template: `
    <na-stack gap="lg">
      @if (error()) { <na-alert tone="danger" showIcon closable (closed)="error.set('')">{{ error() }}</na-alert> }
      <na-row gap="md" justify="between" align="center">
        <na-heading level="3">Guests</na-heading>
        <na-button (pressed)="openForm()">Add guest</na-button>
      </na-row>
      @if (guests().length === 0) {
        <na-empty-state title="No guests" description="Add a guest to start booking." />
      }
      @for (g of guests(); track g.id) {
        <na-card [title]="g.first_name + ' ' + g.last_name" [subtitle]="g.email + (g.phone ? ' · ' + g.phone : '')">
          <na-row gap="sm">
            <na-button size="sm" variant="secondary" (pressed)="showHistory(g)">History</na-button>
            <na-button size="sm" variant="secondary" (pressed)="openForm(g)">Edit</na-button>
            <na-popconfirm message="Delete guest and all their reservations?" (confirmed)="remove(g)">
              <na-button size="sm" variant="danger">Delete</na-button>
            </na-popconfirm>
          </na-row>
        </na-card>
      }
    </na-stack>

    <na-modal [title]="editId ? 'Edit guest' : 'New guest'" [open]="formOpen()" (closed)="formOpen.set(false)">
      <na-stack gap="md">
        @if (formError()) { <na-alert tone="danger" showIcon>{{ formError() }}</na-alert> }
        <na-field label="First name" required><input naInput [(ngModel)]="firstName" /></na-field>
        <na-field label="Last name" required><input naInput [(ngModel)]="lastName" /></na-field>
        <na-field label="Email"><input naInput type="email" [(ngModel)]="email" /></na-field>
        <na-field label="Phone"><input naInput [(ngModel)]="phone" /></na-field>
        <na-row gap="sm" justify="end">
          <na-button variant="ghost" (pressed)="formOpen.set(false)">Close</na-button>
          <na-button (pressed)="save()">Save</na-button>
        </na-row>
      </na-stack>
    </na-modal>

    <na-modal [title]="'Reservations of ' + historyName()" [open]="historyOpen()" (closed)="historyOpen.set(false)">
      <na-stack gap="sm">
        @if (history().length === 0) { <na-text tone="muted">No reservations yet.</na-text> }
        @for (r of history(); track r.id) {
          <na-row gap="sm" align="center" justify="between">
            <na-text>{{ r.date }} {{ hhmm(r.start_time) }} · table {{ r.table_number }} · {{ r.party_size }} guests</na-text>
            <na-badge [tone]="tone[r.status]">{{ label[r.status] }}</na-badge>
          </na-row>
        }
      </na-stack>
    </na-modal>
  `,
})
export class GuestsPage implements OnInit {
  private api = inject(Api);
  private messages = inject(NaMessage);
  readonly tone = STATUS_TONE;
  readonly label = STATUS_LABEL;
  readonly hhmm = hhmm;

  guests = signal<Guest[]>([]);
  error = signal('');
  formError = signal('');
  formOpen = signal(false);
  editId?: number;
  firstName = '';
  lastName = '';
  email = '';
  phone = '';

  historyOpen = signal(false);
  historyName = signal('');
  history = signal<Reservation[]>([]);

  async ngOnInit() {
    await this.load();
  }

  async load() {
    this.guests.set(await this.api.guests());
  }

  openForm(g?: Guest) {
    this.formError.set('');
    this.editId = g?.id;
    this.firstName = g?.first_name ?? '';
    this.lastName = g?.last_name ?? '';
    this.email = g?.email ?? '';
    this.phone = g?.phone ?? '';
    this.formOpen.set(true);
  }

  async save() {
    try {
      await this.api.saveGuest(
        { first_name: this.firstName, last_name: this.lastName, email: this.email, phone: this.phone },
        this.editId,
      );
      this.formOpen.set(false);
      this.messages.success('Guest saved');
      await this.load();
    } catch (e) {
      this.formError.set(errorMessage(e));
    }
  }

  async remove(g: Guest) {
    try {
      await this.api.deleteGuest(g.id);
      await this.load();
    } catch (e) {
      this.error.set(errorMessage(e));
    }
  }

  async showHistory(g: Guest) {
    this.historyName.set(`${g.first_name} ${g.last_name}`);
    this.history.set(await this.api.guestHistory(g.id));
    this.historyOpen.set(true);
  }
}
