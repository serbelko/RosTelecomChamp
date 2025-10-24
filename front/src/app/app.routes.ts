import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth-guard'

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/login/login').then((m) => m.LoginComponent),
  },
  {
    path: '',
    loadComponent: () => import('./core/layout/shell/shell').then((m) => m.ShellComponent),
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard').then((m) => m.DashboardComponent),
      },
      {
        path: 'history',
        loadComponent: () => import('./features/history/history').then((m) => m.HistoryComponent),
      },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
