import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Doctor } from '../models/Doctor.model';

@Component({
  selector: 'app-patient-doclist',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './patient-doclist.component.html',
  styleUrl: './patient-doclist.component.scss',
})

export class PatientDoclistComponent implements OnInit {
  doctors: Doctor[] = [];
  filteredDoctors: Doctor[] = [];
  searchQuery: string = '';
  isLoading: boolean = false;
  error: string = '';

  constructor(private router: Router) {}

  ngOnInit(): void {
    this.fetchDoctors();
  }

  async fetchDoctors(): Promise<void> {
    this.isLoading = true;
    this.error = ''; // Clear previous error
    try {
      const response = await fetch('http://localhost:8080/user/doctors');
      console.log('Response Status:', response.status); // Debugging
      if (!response.ok) throw new Error('Failed to fetch doctors');
  
      const data = await response.json();
      console.log('API Data:', data); // Debugging
      this.doctors = data.map((doctor: Doctor) => ({
        ...doctor,
        description: doctor.description || 'No description available',
      }));
      this.filteredDoctors = [...this.doctors];
    } catch (error: any) {
      this.error = error.message;
      console.error('Fetch Error:', error); // Debugging
    } finally {
      this.isLoading = false;
    }
  }
    
  filterDoctors(): void {
    const query = this.searchQuery.toLowerCase();
    this.filteredDoctors = this.doctors.filter(
      (doctor) =>
        doctor.firstName.toLowerCase().includes(query) ||
        doctor.lastName.toLowerCase().includes(query) ||
        doctor.description?.toLowerCase().includes(query)
    );
  }

  navigateToDoctorView(doctorId: number): void {
    this.router.navigate(['patient-docview', doctorId]);
  }

  navigateTo(route: string): void {
    this.router.navigate([route]);
  }
}