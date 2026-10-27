import { Component } from '@angular/core';
import {
  NaApp, NaFooter, NaHeader, NaPage, NaTab, NaTabs, NaText,
} from 'newang';
import { GuestsPage } from './pages/guests';
import { ReservationsPage } from './pages/reservations';
import { RestaurantsPage } from './pages/restaurants';

@Component({
  selector: 'app-root',
  imports: [NaApp, NaHeader, NaPage, NaFooter, NaTabs, NaTab, NaText, ReservationsPage, RestaurantsPage, GuestsPage],
  template: `
    <na-app>
      <na-header title="TableBooker" subtitle="Restaurant reservations" maxWidth="lg" />
      <na-page maxWidth="lg">
        <na-tabs>
          <na-tab id="reservations" title="Reservations"><app-reservations /></na-tab>
          <na-tab id="restaurants" title="Restaurants & tables"><app-restaurants /></na-tab>
          <na-tab id="guests" title="Guests"><app-guests /></na-tab>
        </na-tabs>
      </na-page>
      <na-footer maxWidth="lg"><na-text tone="faint" size="sm">M450 LB1 · FastAPI + SQLite + Angular/newang</na-text></na-footer>
    </na-app>
  `,
})
export class App {}
