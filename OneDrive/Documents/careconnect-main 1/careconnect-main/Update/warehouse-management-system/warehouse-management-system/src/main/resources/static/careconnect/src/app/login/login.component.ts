import { MatInputModule } from '@angular/material/input';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
  loginForm: FormGroup;
  isLoading = false;
  loginError = '';

  constructor(private fb: FormBuilder, private router: Router) {
    this.loginForm = this.fb.group({
      username: ['', [Validators.required, Validators.minLength(2)]],
      password: ['', [Validators.required, Validators.minLength(3)]],
    });
  }

  // Navigate to Signup Patient page
  navigateToSignupPatient(): void {
    this.router.navigate(['/signup-patient']);
  }

  // Navigate to Signup Doctor page
  navigateToSignupDoctor(): void {
    this.router.navigate(['/signup-doctor']);
  }

  // Handle form submission
  handleSubmit(): void {
    if (this.loginForm.invalid) {
      return;
    }

    this.isLoading = true;
    this.loginError = '';

    const payload = this.loginForm.value;

    // Make the login API call
    fetch('http://localhost:8080/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to login. Status: ' + response.status);
        }
        return response.json();
      })
      .then((data) => {
        console.log('Login successful:', data);

        // Store token and username
        localStorage.setItem('token', data.token);
        localStorage.setItem('username', payload.username);

        // Fetch user details to get userType
        return fetch('http://localhost:8080/user/details', {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${data.token}`,
            'Content-Type': 'application/json',
          },
        });
      })
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            'Failed to fetch user details. Status: ' + response.status
          );
        }
        return response.json();
      })
      .then((userDetails) => {
        const userType = userDetails.userType;
        const userId = userDetails.userId;
        console.log('User type:', userType);

        // Store userType and userId in localStorage
        localStorage.setItem('userType', userType);
        localStorage.setItem('userId', userId);

        // Navigate based on userType
        switch (userType) {
          case 'patient':
            this.router.navigate(['/patient-home']);
            break;
          case 'doctor':
            this.router.navigate(['/doctor-home']);
            break;
          default:
            throw new Error('Invalid user type');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        this.loginError = error.message || 'Login failed. Please try again.';
      })
      .finally(() => {
        this.isLoading = false;
      });
  }
}
