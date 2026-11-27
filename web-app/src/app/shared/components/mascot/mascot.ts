import { Component, input } from '@angular/core';

@Component({
  selector: 'app-mascot',
  templateUrl: './mascot.html',
  styleUrl: './mascot.css',
})
export class Mascot {
  size = input(120);
}