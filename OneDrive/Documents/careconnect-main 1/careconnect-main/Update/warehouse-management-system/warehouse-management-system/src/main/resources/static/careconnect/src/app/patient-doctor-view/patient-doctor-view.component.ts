import { Component, OnInit } from '@angular/core';
import { Doctor } from '../models/Doctor.model';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-patient-doctor-view',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './patient-doctor-view.component.html',
  styleUrl: './patient-doctor-view.component.scss',
})

export class PatientDoctorViewComponent implements OnInit {
  doctor: Doctor | null = null;
  isLoading = false;
  error = '';

  constructor(
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.fetchDoctorDetails();
  }

  async fetchDoctorDetails(): Promise<void> {
    this.isLoading = true;
    try {
      const doctorId = this.route.snapshot.paramMap.get('id');
      if (!doctorId) throw new Error('Doctor ID not found');

      const response = await fetch(`http://localhost:8080/user/find/${doctorId}`);
      if (!response.ok) throw new Error('Failed to fetch doctor details');

      this.doctor = await response.json();
    } catch (error: any) {
      this.error = error.message;
    } finally {
      this.isLoading = false;
    }
  }

  navigateTo(route: string): void {
    this.router.navigate([route]);
  }
}