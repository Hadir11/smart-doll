import { Component, inject } from '@angular/core';
import { Auth } from '../../core/services/auth';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  auth = inject(Auth);

  child = { name: 'Lina', age: 6, time: '3h 25 min', level: 'Niveau 1' };

  stats = [
    { icon: '🕒', value: '3h 25 min', label: "Temps d'apprentissage", trend: '+12%' },
    { icon: '✅', value: '18', label: 'Leçons réalisées', trend: '+20%' },
    { icon: '🏆', value: '84%', label: 'Taux de réussite', trend: '+8%' },
    { icon: '⭐', value: '7 / 10', label: 'Compétences maîtrisées', trend: '+1' },
  ];

  subjects = [
    { name: 'Mathématiques', value: 85, color: 'bg-sky-500' },
    { name: 'Lecture', value: 72, color: 'bg-primary' },
    { name: 'Sciences', value: 90, color: 'bg-success' },
    { name: 'Langue', value: 65, color: 'bg-warning' },
  ];

  activities = [
    { icon: '➕', title: 'Additions simples', meta: "Score : 8/10 • Aujourd'hui, 18:20" },
    { icon: '📖', title: 'Les animaux', meta: "Score : 10/10 • Aujourd'hui, 17:45" },
    { icon: '🧪', title: 'Les couleurs', meta: 'Score : 7/10 • Hier, 16:30' },
  ];

  notifications = [
    { icon: '📈', text: 'Nouvelle progression : +20% en mathématiques', time: 'Il y a 1h' },
    { icon: '✅', text: 'Session terminée avec succès', time: 'Il y a 2h' },
    { icon: '💡', text: 'Conseil : privilégiez les activités de lecture', time: 'Hier' },
  ];

  // ---- Graphique hebdomadaire (SVG) ----
  private x0 = 50; private x1 = 680; private y0 = 15; private y1 = 185;
  weekly = [
    { day: 'Lun', value: 25 }, { day: 'Mar', value: 35 }, { day: 'Mer', value: 42 },
    { day: 'Jeu', value: 58 }, { day: 'Ven', value: 65 }, { day: 'Sam', value: 92 },
    { day: 'Dim', value: 82 },
  ];
  maxValue = Math.max(...this.weekly.map(d => d.value));

  private yOf(v: number) { return this.y1 - (v / 100) * (this.y1 - this.y0); }

  points = this.weekly.map((d, i) => ({
    ...d,
    x: this.x0 + (i * (this.x1 - this.x0)) / (this.weekly.length - 1),
    y: this.yOf(d.value),
  }));
  ticks = [100, 75, 50, 25, 0].map(v => ({ v, y: this.yOf(v) }));
  linePath = 'M' + this.points.map(p => `${p.x},${p.y}`).join(' L');
  areaPath = `${this.linePath} L${this.x1},${this.y1} L${this.x0},${this.y1} Z`;
}