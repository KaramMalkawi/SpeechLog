import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common'; // Import CommonModule

@Component({
  selector: 'app-patient-home',
  standalone: true, // Add this if using standalone components
  imports: [CommonModule], // Add CommonModule here
  templateUrl: './patient-home.component.html',
  styleUrl: './patient-home.component.scss',
})

export class PatientHomeComponent implements OnInit {
  departments: any[] = [];
  isLoading = false;

  constructor(private router: Router) {
    console.log('JWT Token:', localStorage.getItem('token')); // Debugging
  }

  ngOnInit(): void {
    this.loadDepartments();
  }

  navigateTo(route: string): void {
    this.router.navigate([route]);
  }

  async loadDepartments(): Promise<void> {

    this.isLoading = true;
    console.log('Loading departments...'); // Debugging

    try {
      const response = await fetch('http://localhost:8080/departments/all', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
  
      console.log('API Response:', response); // Debugging
  
      if (!response.ok) {
        throw new Error(`Failed to load departments. Status: ${response.status}`);
      }
  
      const data = await response.json();
      console.log('Departments Data:', data); // Debugging
      this.departments = data;

    } catch (error: any) {
      console.error('Error:', error.message); // Debugging
    } finally {
      this.isLoading = false;
      console.log('Departments loading complete.'); // Debugging
    }
  }
}
