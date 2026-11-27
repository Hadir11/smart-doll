import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Mascot } from '../../shared/components/mascot/mascot';

@Component({
  selector: 'app-landing',
  imports: [RouterLink, Mascot],
  templateUrl: './landing.html',
  styleUrl: './landing.css',
})
export class Landing {
  perks = ['Apprentissage personnalisé', 'Contrôle parental sécurisé', 'Un compagnon éducatif'];
}