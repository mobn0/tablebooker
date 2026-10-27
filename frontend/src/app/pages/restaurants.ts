import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  NaAlert, NaBadge, NaButton, NaCard, NaEmptyState, NaField, NaHeading, NaInput, NaMessage,
  NaModal, NaPopconfirm, NaRow, NaSelect, NaSelectOption, NaStack,
} from 'newang';
import { Api, DiningTable, Restaurant, errorMessage, hhmm } from '../api';

@Component({
  selector: 'app-restaurants',
  imports: [
    FormsModule, NaAlert, NaBadge, NaButton, NaCard, NaEmptyState, NaField, NaHeading, NaInput,
    NaModal, NaPopconfirm, NaRow, NaSelect, NaStack,
  ],
  template: `
    <na-stack gap="lg">
      @if (error()) { <na-alert tone="danger" showIcon closable (closed)="error.set('')">{{ error() }}</na-alert> }

      <na-row gap="md" justify="between" align="center">
        <na-heading level="3">Restaurants</na-heading>
        <na-button (pressed)="openRestaurant()">Add restaurant</na-button>
      </na-row>
      @if (restaurants().length === 0) {
        <na-empty-state title="No restaurants" description="Add your first restaurant." />
      }
      @for (r of restaurants(); track r.id) {
        <na-card [title]="r.name" [subtitle]="r.address + ' · open ' + hhmm(r.opening_time) + '–' + hhmm(r.closing_time)">
          <na-row gap="sm">
            <na-button size="sm" variant="secondary" (pressed)="openRestaurant(r)">Edit</na-button>
            <na-popconfirm message="Delete restaurant with all its tables?" (confirmed)="removeRestaurant(r)">
              <na-button size="sm" variant="danger">Delete</na-button>
            </na-popconfirm>
          </na-row>
        </na-card>
      }

      <na-row gap="md" justify="between" align="center">
        <na-heading level="3">Tables</na-heading>
        <na-row gap="md" align="center">
          <na-select [options]="restaurantOptions()" [(value)]="selected" (valueChange)="loadTables()" placeholder="Choose a restaurant" />
          <na-button [disabled]="!selected()" (pressed)="openTable()">Add table</na-button>
        </na-row>
      </na-row>
      @if (selected() && tables().length === 0) {
        <na-empty-state title="No tables" description="This restaurant has no tables yet." />
      }
      @for (t of tables(); track t.id) {
        <na-card [title]="'Table ' + t.number" [subtitle]="t.seats + ' seats'">
          <na-row gap="sm" align="center">
            <na-badge tone="neutral">{{ t.location }}</na-badge>
            <na-button size="sm" variant="secondary" (pressed)="openTable(t)">Edit</na-button>
            <na-popconfirm message="Delete this table?" (confirmed)="removeTable(t)">
              <na-button size="sm" variant="danger">Delete</na-button>
            </na-popconfirm>
          </na-row>
        </na-card>
      }
    </na-stack>

    <na-modal [title]="editRestaurantId ? 'Edit restaurant' : 'New restaurant'" [open]="restaurantModal()" (closed)="restaurantModal.set(false)">
      <na-stack gap="md">
        @if (formError()) { <na-alert tone="danger" showIcon>{{ formError() }}</na-alert> }
        <na-field label="Name" required><input naInput [(ngModel)]="rName" /></na-field>
        <na-field label="Address"><input naInput [(ngModel)]="rAddress" /></na-field>
        <na-field label="Opening time"><input naInput type="time" [(ngModel)]="rOpen" /></na-field>
        <na-field label="Closing time"><input naInput type="time" [(ngModel)]="rClose" /></na-field>
        <na-row gap="sm" justify="end">
          <na-button variant="ghost" (pressed)="restaurantModal.set(false)">Close</na-button>
          <na-button (pressed)="saveRestaurant()">Save</na-button>
        </na-row>
      </na-stack>
    </na-modal>

    <na-modal [title]="editTableId ? 'Edit table' : 'New table'" [open]="tableModal()" (closed)="tableModal.set(false)">
      <na-stack gap="md">
        @if (formError()) { <na-alert tone="danger" showIcon>{{ formError() }}</na-alert> }
        <na-field label="Table number" required><input naInput type="number" min="1" [(ngModel)]="tNumber" /></na-field>
        <na-field label="Seats" required><input naInput type="number" min="1" max="30" [(ngModel)]="tSeats" /></na-field>
        <na-field label="Location">
          <na-select [options]="locationOptions" [(value)]="tLocation" />
        </na-field>
        <na-row gap="sm" justify="end">
          <na-button variant="ghost" (pressed)="tableModal.set(false)">Close</na-button>
          <na-button (pressed)="saveTable()">Save</na-button>
        </na-row>
      </na-stack>
    </na-modal>
  `,
})
export class RestaurantsPage implements OnInit {
  private api = inject(Api);
  private messages = inject(NaMessage);
  readonly hhmm = hhmm;

  restaurants = signal<Restaurant[]>([]);
  tables = signal<DiningTable[]>([]);
  selected = signal<string | number | undefined>(undefined);
  error = signal('');
  formError = signal('');

  restaurantOptions = computed<NaSelectOption[]>(() =>
    this.restaurants().map((r) => ({ value: r.id, label: r.name })),
  );
  readonly locationOptions: NaSelectOption[] = [
    { value: 'inside', label: 'Inside' },
    { value: 'terrace', label: 'Terrace' },
  ];

  restaurantModal = signal(false);
  editRestaurantId?: number;
  rName = '';
  rAddress = '';
  rOpen = '11:00';
  rClose = '23:00';

  tableModal = signal(false);
  editTableId?: number;
  tNumber = 1;
  tSeats = 2;
  tLocation = signal<string | number | undefined>('inside');

  async ngOnInit() {
    await this.loadRestaurants();
    if (this.restaurants().length) {
      this.selected.set(this.restaurants()[0].id);
      await this.loadTables();
    }
  }

  async loadRestaurants() {
    this.restaurants.set(await this.api.restaurants());
  }

  async loadTables() {
    const id = Number(this.selected());
    this.tables.set(id ? await this.api.tables(id) : []);
  }

  openRestaurant(r?: Restaurant) {
    this.formError.set('');
    this.editRestaurantId = r?.id;
    this.rName = r?.name ?? '';
    this.rAddress = r?.address ?? '';
    this.rOpen = r ? hhmm(r.opening_time) : '11:00';
    this.rClose = r ? hhmm(r.closing_time) : '23:00';
    this.restaurantModal.set(true);
  }

  async saveRestaurant() {
    try {
      await this.api.saveRestaurant(
        { name: this.rName, address: this.rAddress, opening_time: this.rOpen + ':00', closing_time: this.rClose + ':00' },
        this.editRestaurantId,
      );
      this.restaurantModal.set(false);
      this.messages.success('Restaurant saved');
      await this.loadRestaurants();
      if (!this.selected() && this.restaurants().length) {
        this.selected.set(this.restaurants()[0].id);
        await this.loadTables();
      }
    } catch (e) {
      this.formError.set(errorMessage(e));
    }
  }

  async removeRestaurant(r: Restaurant) {
    try {
      await this.api.deleteRestaurant(r.id);
      if (Number(this.selected()) === r.id) this.selected.set(undefined);
      await this.loadRestaurants();
      await this.loadTables();
    } catch (e) {
      this.error.set(errorMessage(e));
    }
  }

  openTable(t?: DiningTable) {
    this.formError.set('');
    this.editTableId = t?.id;
    this.tNumber = t?.number ?? (this.tables().reduce((m, x) => Math.max(m, x.number), 0) + 1);
    this.tSeats = t?.seats ?? 2;
    this.tLocation.set(t?.location ?? 'inside');
    this.tableModal.set(true);
  }

  async saveTable() {
    try {
      await this.api.saveTable(
        {
          restaurant_id: Number(this.selected()),
          number: Number(this.tNumber),
          seats: Number(this.tSeats),
          location: String(this.tLocation()),
        },
        this.editTableId,
      );
      this.tableModal.set(false);
      this.messages.success('Table saved');
      await this.loadTables();
    } catch (e) {
      this.formError.set(errorMessage(e));
    }
  }

  async removeTable(t: DiningTable) {
    try {
      await this.api.deleteTable(t.id);
      await this.loadTables();
    } catch (e) {
      this.error.set(errorMessage(e));
    }
  }
}
