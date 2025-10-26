// src/app/features/register/register.ts
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AuthService } from '../../core/auth/auth';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './register.html',
  styleUrls: ['./register.scss'],
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private snack = inject(MatSnackBar);

  loading = false;

  form = this.fb.group({
    name: ['', [Validators.required]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirm: ['', [Validators.required]],
    agree: [true, [Validators.requiredTrue]],
  });

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const name = this.form.get('name')?.value ?? '';
    const email = this.form.get('email')?.value ?? '';
    const password = this.form.get('password')?.value ?? '';
    const confirm = this.form.get('confirm')?.value ?? '';

    if (password !== confirm) {
      this.snack.open('Пароли не совпадают', 'OK', { duration: 3000 });
      return;
    }

    this.loading = true;

    // ВАЖНО: предполагаем, что AuthService.register(...) возвращает Observable<boolean>,
    // где true = токен выдан (мы уже сохранили сессию), false = токена нет (идём на /login)
    this.auth.register({ name, email, password }).subscribe({
      next: (hasToken: boolean) => {
        this.loading = false;
        this.snack.open('Регистрация успешна', 'OK', { duration: 2000 });
        this.router.navigateByUrl(hasToken ? '/dashboard' : '/login');
      },
      error: (err) => {
        this.loading = false;

        if (err?.status === 409) {
          // конфликт: пользователь с таким email уже существует
          const msg =
            err.error?.message || err.error?.detail || 'Пользователь с таким email уже существует';
          this.snack.open(msg, 'OK', { duration: 3500 });
          return;
        }

        if (err?.status === 400) {
          const msg = err.error?.message || 'Некорректные данные';
          this.snack.open(msg, 'OK', { duration: 3500 });
          return;
        }

        // дефолтный вариант
        this.snack.open('Ошибка регистрации. Попробуйте ещё раз', 'OK', { duration: 3500 });
      },
    });
  }
}
