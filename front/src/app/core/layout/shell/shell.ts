import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { NgIf } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';

import { AuthStore } from '../../auth/auth.store';
import { AuthService } from '../../auth/auth';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    // router
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    // common
    NgIf,
    // material
    MatToolbarModule,
    MatButtonModule,
  ],
  templateUrl: './shell.html',
  styleUrls: ['./shell.scss'],
})
export class ShellComponent {
  store = inject(AuthStore);
  private auth = inject(AuthService);
  private router = inject(Router);

  logout() {
    this.auth.logout();
    this.router.navigateByUrl('/login');
  }
}
