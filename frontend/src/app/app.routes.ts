import { Routes } from '@angular/router';
import { RfpDashboardComponent } from './components/rfp-dashboard/rfp-dashboard.component';
import { RfpDetailComponent } from './components/rfp-detail/rfp-detail.component';
import { LibrarySearchComponent } from './components/library-search/library-search.component';

export const routes: Routes = [
  { path: '', component: RfpDashboardComponent },
  { path: 'rfp/:id', component: RfpDetailComponent },
  { path: 'library', component: LibrarySearchComponent },
  { path: '**', redirectTo: '' },
];
