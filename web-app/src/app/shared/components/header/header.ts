import { Component, inject } from '@angular/core';
import { Auth } from '../../../core/services/auth';

@Component({
  selector: 'app-header',
  templateUrl: './header.html',
  styleUrl: './header.css',
})
export class Header {
  auth = inject(Auth);
}