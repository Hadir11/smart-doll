import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { Auth } from '../../../core/services/auth';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css',
})
export class Sidebar {
  private auth = inject(Auth);
  private router = inject(Router);

  links = [
    { label: 'Dashboard', path: '/app/dashboard', icon: '🏠' },
    { label: 'Profil Enfant', path: '/app/profil', icon: '👧' },
    { label: 'Progression', path: '/app/progression', icon: '📊' },
    { label: 'Activités & Leçons', path: '/app/activites', icon: '📘' },
    { label: 'Historique', path: '/app/historique', icon: '🕘' },
    { label: 'Ma Poupée', path: '/app/poupee', icon: '🧸' },
    { label: 'Paramètres', path: '/app/parametres', icon: '⚙️' },
  ];

  logout() {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}