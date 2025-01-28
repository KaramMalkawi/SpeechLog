import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Router } from '@angular/router';

@Component({
  selector: 'app-signup-patient',
  standalone: true,
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
  templateUrl: './signup-patient.component.html',
  styleUrl: './signup-patient.component.scss'
})

export class SignupPatientComponent implements OnInit {
  signupForm: FormGroup;
  isLoading = false;
  errorMessage: string | null = null;
  submitError: string | null = null;

  constructor(private fb: FormBuilder, private router: Router) {
    this.signupForm = this.fb.group({
      firstName: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(25), Validators.pattern('[a-zA-Z ]*')]],
      lastName: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(25), Validators.pattern('[a-zA-Z ]*')]],
      username: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      phoneNumber: ['', Validators.required],
      password: ['', [Validators.required, Validators.minLength(8), Validators.pattern('(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[$@$!%*?&])[A-Za-z\\d$@$!%*?&].{8,}')]],
      userType: ['patient', Validators.required],
    });
  }

  ngOnInit(): void {}

  navigateToLogin(): void {
    this.router.navigate(['/']);
  }

  handleSubmit(): void {
    if (this.signupForm.valid) {
      this.isLoading = true;
      this.errorMessage = null;
      this.submitError = null; // Reset submitError
  
      const payload = this.signupForm.value;
      console.log('Payload:', payload); // Debugging: Check the payload
  
      fetch('http://localhost:8080/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
        .then((response) => {
          console.log('Response:', response); // Debugging: Check the response
          if (!response.ok) {
            return response.text().then((text) => {
              console.error('Error Response Text:', text); // Debugging: Check the error text
              try {
                const data = JSON.parse(text);
                throw new Error(data.message || text);
              } catch (error) {
                throw new Error(text);
              }
            });
          }
          return response.json();
        })
        .then((data) => {
          console.log('User created successfully:', data);
          this.signupForm.reset();
          this.router.navigate(['']);
        })
        .catch((error) => {
          console.error('Error:', error); // Debugging: Log the full error
          this.errorMessage = error.message || 'Signup failed';
          this.submitError = error.message || 'Signup failed'; // Set submitError
        })
        .finally(() => {
          this.isLoading = false;
        });
    }
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      this.signupForm.patchValue({ profilePhoto: file });
      this.signupForm.get('profilePhoto')?.updateValueAndValidity();
    }
  }
}